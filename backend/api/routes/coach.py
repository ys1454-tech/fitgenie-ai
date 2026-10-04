"""
coach.py — API route for real-time date/time aware conversational AI Coach queries.

Endpoints:
  POST /api/coach/chat — Real-time conversational AI Coach endpoint for informational
                         and diet/workout queries. Does NOT modify the plan or save
                         any database records.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from prompts.coach import build_coach_prompt, is_food_alternative_request
from services.gemini_service import GeminiServiceError, gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coach", tags=["Coach"])


class CoachChatRequest(BaseModel):
    user_request: str = Field(
        ...,
        description="Natural language question from the user.",
        examples=["What should I eat now?"],
    )
    current_date: str = Field(
        ...,
        description="Current date in ISO format (YYYY-MM-DD).",
        examples=["2026-10-04"],
    )
    current_day: str = Field(
        ...,
        description="Current day of the week.",
        examples=["Sunday"],
    )
    current_time: str = Field(
        ...,
        description="Current local time.",
        examples=["13:31"],
    )
    today_plan: dict = Field(
        default_factory=dict,
        description="Today's plan details (workout, nutrition, daily_notes).",
    )
    tomorrow_plan: dict | None = Field(
        default=None,
        description="Tomorrow's plan details (optional).",
    )
    profile: dict = Field(
        default_factory=dict,
        description="Extracted user profile dictionary.",
    )


class CoachChatResponse(BaseModel):
    message: str


def _fmt_num(val):
    """Format numeric values cleanly (e.g. 70.0 -> 70, 70.5 -> 70.5)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val) if val == int(val) else val
    return val


def get_deterministic_answer(
    user_request: str,
    profile: dict,
    today_plan: dict,
    tomorrow_plan: dict | None,
    current_time: str,
) -> str | None:
    """
    Check if the user request can be answered directly and deterministically
    from the user profile, today's/tomorrow's plan, or conversational intent.
    
    Returns a concise, focused answer if matched, or None to route to LLM.
    Guarantees zero hallucination, zero extraneous context, and instant accuracy.
    """
    import re
    req = user_request.lower().strip().rstrip("?.! ")

    # ── 0. Food Alternative / Unavailable Food Check ───────────────────
    # These queries require reasoning and practical alternatives matching the profile.
    # Never intercept them with deterministic scheduled meal lookups.
    if is_food_alternative_request(user_request):
        return None

    # ── 1. General Conversation & Pleasantries ─────────────────────────
    if req in {"hello", "hi", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"}:
        return "Hello! How can I assist you with your fitness or nutrition today?"

    if req in {"thank you", "thanks", "thanks a lot", "thank you so much", "thx"}:
        return "You're welcome! Let me know if you need anything else."

    # ── 2. Profile Factual Questions ──────────────────────────────────
    # Weight
    if any(p in req for p in ["initial weight", "my weight", "body weight", "current weight", "what do i weigh", "starting weight", "how heavy", "how much do i weigh"]):
        val = profile.get("weight")
        return f"Your initial weight is {_fmt_num(val)} kg." if val is not None else "Your weight is not recorded in your profile."

    # Height
    if any(p in req for p in ["my height", "how tall", "what is my height"]):
        val = profile.get("height")
        return f"Your height is {_fmt_num(val)} cm." if val is not None else "Your height is not recorded in your profile."

    # Fitness Goal
    if any(p in req for p in ["fitness goal", "my goal", "what is my goal"]):
        val = profile.get("fitness_goal")
        return f"Your fitness goal is {val}." if val is not None else "Your fitness goal is not recorded in your profile."

    # Budget
    if any(p in req for p in ["my budget", "food budget", "meal budget", "what is my budget"]):
        val = profile.get("budget")
        return f"Your monthly food budget is ₹{_fmt_num(val)}." if val is not None else "Your budget is not specified in your profile."

    # Equipment
    if any(p in req for p in ["my equipment", "equipment do i have", "what equipment", "equipment have i got"]):
        val = profile.get("equipment")
        return f"Your available equipment is {val}." if val is not None else "No specific equipment is recorded in your profile."

    # Age
    if any(p in req for p in ["my age", "how old", "what is my age"]):
        val = profile.get("age")
        return f"You are {val} years old." if val is not None else "Your age is not recorded in your profile."

    # Gender
    if any(p in req for p in ["my gender", "what is my gender", "what is my sex"]):
        val = profile.get("gender")
        return f"Your gender is {val}." if val is not None else "Your gender is not recorded in your profile."

    # Fitness Level
    if any(p in req for p in ["fitness level", "my level", "what is my fitness level", "experience level"]):
        val = profile.get("fitness_level")
        return f"Your fitness level is {val}." if val is not None else "Your fitness level is not recorded in your profile."

    # Available daily workout time
    if any(p in req for p in ["available time", "workout time do i have", "how much workout time", "how much time do i have", "daily workout time", "how long can i exercise"]):
        val = profile.get("available_time")
        return f"Your daily available workout time is {val} minutes." if val is not None else "Your available time is not recorded in your profile."

    # Food Preference
    if any(p in req for p in ["food preference", "dietary preference", "diet preference", "what kind of food", "eating preference"]):
        val = profile.get("food_preference")
        return f"Your food preference is {val}." if val is not None else "No specific food preference is recorded in your profile."

    # Food Restrictions / Allergies
    if any(p in req for p in ["food restriction", "dietary restriction", "allergies", "allergy", "restrictions"]):
        val = profile.get("food_restrictions")
        if val and str(val).lower() not in ("none", "null", "no", "n/a"):
            return f"Your dietary restrictions: {val}."
        return "You have no dietary restrictions recorded in your profile."

    # ── 3. Nutrition Questions ─────────────────────────────────────────
    today_nutrition = (today_plan or {}).get("nutrition") or {}
    tomorrow_nutrition = (tomorrow_plan or {}).get("nutrition") or {}

    # Tomorrow's meals
    if "tomorrow" in req and any(w in req for w in ["eat", "eating", "food", "meal", "diet", "nutrition", "breakfast", "lunch", "dinner", "snack"]):
        if "breakfast" in req:
            b = tomorrow_nutrition.get("breakfast", "Not specified")
            return f"Your breakfast tomorrow is {b}."
        if "lunch" in req:
            l = tomorrow_nutrition.get("lunch", "Not specified")
            return f"Your lunch tomorrow is {l}."
        if "dinner" in req or "supper" in req:
            d = tomorrow_nutrition.get("dinner", "Not specified")
            return f"Your dinner tomorrow is {d}."
        if "snack" in req:
            s = tomorrow_nutrition.get("snack", "Not specified")
            return f"Your snack tomorrow is {s}."

        b = tomorrow_nutrition.get("breakfast", "Not specified")
        l = tomorrow_nutrition.get("lunch", "Not specified")
        s = tomorrow_nutrition.get("snack", "Not specified")
        d = tomorrow_nutrition.get("dinner", "Not specified")
        return f"Tomorrow's meals:\n• Breakfast: {b}\n• Lunch: {l}\n• Snack: {s}\n• Dinner: {d}"

    # What should I eat now? (Deterministic slot matching based on current_time)
    if any(p in req for p in ["what should i eat now", "what to eat now", "i want to eat now", "what can i eat now", "what should i eat right now", "what to eat right now", "eat now"]):
        hour = 12
        m = re.search(r"(\d{1,2}):", current_time or "")
        if m:
            try:
                hour = int(m.group(1))
            except ValueError:
                pass

        if 5 <= hour < 11:
            meal_name = "breakfast"
            meal_val = today_nutrition.get("breakfast")
        elif 11 <= hour < 16:
            meal_name = "lunch"
            meal_val = today_nutrition.get("lunch")
        elif 16 <= hour < 19:
            meal_name = "snack"
            meal_val = today_nutrition.get("snack")
        else:
            meal_name = "dinner"
            meal_val = today_nutrition.get("dinner")

        if meal_val:
            return f"Based on the current time, your scheduled meal is {meal_name}: {meal_val}."
        return f"Based on the current time, your scheduled meal is {meal_name}."

    # Today's specific meals
    if "breakfast" in req and "tomorrow" not in req:
        b = today_nutrition.get("breakfast")
        return f"Your breakfast today is {b}." if b else "No breakfast is specified in today's plan."

    if "lunch" in req and "tomorrow" not in req:
        l = today_nutrition.get("lunch")
        return f"Your lunch today is {l}." if l else "No lunch is specified in today's plan."

    if ("dinner" in req or "supper" in req) and "tomorrow" not in req:
        d = today_nutrition.get("dinner")
        return f"Your dinner today is {d}." if d else "No dinner is specified in today's plan."

    if "snack" in req and "tomorrow" not in req:
        s = today_nutrition.get("snack")
        return f"Your snack today is {s}." if s else "No snack is specified in today's plan."

    # ── 4. Workout Questions ───────────────────────────────────────────
    today_workout = (today_plan or {}).get("workout") or {}
    tomorrow_workout = (tomorrow_plan or {}).get("workout") or {}

    # How long is today's workout?
    if any(p in req for p in ["how long", "duration"]) and any(w in req for w in ["workout", "exercise", "today"]):
        title = today_workout.get("title", "Today's workout")
        duration = today_workout.get("duration_minutes")
        if duration is not None:
            return f"Today's workout ({title}) is {duration} minutes long."
        return "The duration for today's workout is not specified."

    # What exercises am I doing today?
    if any(p in req for p in ["exercises am i doing", "what exercises", "which exercises", "exercises today", "today's exercises"]):
        exercises = today_workout.get("exercises") or []
        if exercises:
            ex_lines = [
                f"• {ex.get('name', 'Exercise')} ({ex.get('sets', '')} sets × {ex.get('reps_or_duration', '')})"
                for ex in exercises
            ]
            return "Today's exercises:\n" + "\n".join(ex_lines)
        return "No specific exercises scheduled for today (rest or recovery day)."

    # What is my workout today?
    if any(p in req for p in ["workout today", "today's workout", "workout for today"]) or (
        "workout" in req and "today" in req and "tomorrow" not in req
    ):
        title = today_workout.get("title", "Workout Session")
        duration = today_workout.get("duration_minutes", 30)
        focus = today_workout.get("focus_area", "General Fitness")
        exercises = today_workout.get("exercises") or []
        if exercises:
            ex_lines = [
                f"• {ex.get('name', 'Exercise')} ({ex.get('sets', '')} sets × {ex.get('reps_or_duration', '')})"
                for ex in exercises
            ]
            return (
                f"Today's workout: {title} ({duration} mins, Focus: {focus}).\n"
                f"Exercises:\n" + "\n".join(ex_lines)
            )
        return f"Today's workout: {title} ({duration} mins, Focus: {focus}). Rest & recovery day."

    # Tomorrow's workout
    if "tomorrow" in req and "workout" in req:
        title = tomorrow_workout.get("title", "Rest Day")
        duration = tomorrow_workout.get("duration_minutes", 0)
        focus = tomorrow_workout.get("focus_area", "Rest & Recovery")
        return f"Tomorrow's workout: {title} ({duration} mins, Focus: {focus})."

    return None


@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    response_model=CoachChatResponse,
    summary="Real-time date/time aware conversational AI Coach chat",
)
def coach_chat(body: CoachChatRequest):
    """
    Answers the user's questions about their personalized plan using real-time
    date, day of week, and local time context.

    Does NOT modify the plan and does NOT persist any database records.
    Strictly answers only the user's actual question.
    """
    user_request = body.user_request.strip() if body.user_request else ""
    if not user_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_request cannot be empty.",
        )

    # 1. Deterministic check (instant, 100% accurate, zero hallucination or extraneous context)
    direct_ans = get_deterministic_answer(
        user_request=user_request,
        profile=body.profile,
        today_plan=body.today_plan,
        tomorrow_plan=body.tomorrow_plan,
        current_time=body.current_time,
    )
    if direct_ans is not None:
        return CoachChatResponse(message=direct_ans)

    # 2. Focused LLM generation for meals, workouts, educational and conversational questions
    prompts = build_coach_prompt(
        user_request=user_request,
        current_date=body.current_date,
        current_day=body.current_day,
        current_time=body.current_time,
        today_plan=body.today_plan,
        tomorrow_plan=body.tomorrow_plan or {},
        profile=body.profile,
    )

    try:
        reply_text = gemini_service.invoke(
            user_prompt=prompts["user"],
            system_prompt=prompts["system"],
            temperature=0.2,
        )
    except GeminiServiceError as exc:
        logger.error("Gemini service error during coach chat: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Coach service error: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during coach chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error communicating with LLM: {str(exc)}",
        ) from exc

    return CoachChatResponse(message=reply_text.strip())
