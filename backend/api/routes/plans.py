"""
plans.py — API routes for 7-day fitness and nutrition plan generation and modification.

Endpoints:
  POST /api/plans/generate        — End-to-end plan generation from natural language input.
  POST /api/plans/{id}/modify     — Conversational modification of an existing generated plan.
  POST /api/plans/{id}/coach      — Real-time aware AI Coach: answers informational questions
                                    using current date/time context without modifying the plan.
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from nlp.pipeline import analyze_text

from database.crud import (
    create_user_session,
    get_plan_by_id,
    get_user_session,
    save_plan,
)
from database.db import get_db
from prompts.plan_generation import build_plan_generation_prompt
from prompts.plan_modification import build_plan_modification_prompt
from prompts.profile_extraction import build_profile_extraction_prompt
from prompts.substitution import build_substitution_prompt
from services.nutrition import NutritionValidationError, apply_food_substitution
from services.gemini_service import GeminiServiceError, gemini_service
from services.response_parser import (
    LLMResponseError,
    parse_llm_json,
    validate_plan_modification_response,
    validate_plan_response,
    validate_profile_extraction_response,
    validate_substitution_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plans", tags=["Plans"])
PLAN_RESPONSE_MAX_TOKENS = 8192


def _invoke_validated_plan(prompts: dict, profile: dict) -> dict:
    user_prompt = prompts["user"]
    for attempt in range(2):
        raw_response = gemini_service.invoke(
            user_prompt=user_prompt,
            system_prompt=prompts["system"],
            temperature=0.3,
            max_tokens=PLAN_RESPONSE_MAX_TOKENS,
            response_mime_type="application/json",
        )
        try:
            return validate_plan_response(parse_llm_json(raw_response), profile)
        except LLMResponseError as exc:
            if attempt == 1:
                raise LLMResponseError(
                    f"Plan response remained invalid after one retry: {exc.message}",
                    raw_response=raw_response,
                ) from exc
            user_prompt = (
                f"{prompts['user']}\n\n"
                "Your previous response failed validation: "
                f"{exc.message} Return a complete corrected JSON object with all seven numbered days, "
                "including workout and nutrition sections for every day. Do not omit any required fields."
            )
    raise AssertionError("Unreachable plan retry state.")


def _invoke_validated_modification(prompts: dict, existing_plan: dict, profile: dict) -> dict:
    user_prompt = prompts["user"]
    for attempt in range(2):
        raw_response = gemini_service.invoke(
            user_prompt=user_prompt,
            system_prompt=prompts["system"],
            temperature=0.3,
            max_tokens=PLAN_RESPONSE_MAX_TOKENS,
            response_mime_type="application/json",
        )
        try:
            return validate_plan_modification_response(
                parse_llm_json(raw_response), existing_plan, profile
            )
        except LLMResponseError as exc:
            if attempt == 1:
                raise LLMResponseError(
                    f"Plan modification remained invalid after one retry: {exc.message}",
                    raw_response=raw_response,
                ) from exc
            user_prompt = (
                f"{prompts['user']}\n\n"
                "Your previous response failed validation: "
                f"{exc.message} Return a compact JSON object with a 'day_updates' list containing "
                "only affected days and changed fields. Include updated nutrition estimates for every changed meal."
            )
    raise AssertionError("Unreachable modification retry state.")


# ── Request / Response Schemas ─────────────────────────────────────────────

class PlanGenerateRequest(BaseModel):
    user_input: str = Field(
        ...,
        description="Natural language description of user fitness profile, goals, and constraints.",
        examples=[
            "I am 21 years old, male, 175 cm tall, 70 kg. My goal is weight loss. "
            "I am a beginner. I can exercise for 45 minutes per day. I have dumbbells at home. "
            "I prefer Indian vegetarian food. My budget is 3000 rupees per month."
        ],
    )


class PlanModifyRequest(BaseModel):
    user_request: str = Field(
        ...,
        description="Natural language request detailing the desired modifications to the existing plan.",
        examples=["Make Wednesday's workout only 20 minutes."],
    )
    current_day: str | None = Field(
        default=None,
        description="Current day of the week to resolve relative references like 'today'.",
        examples=["Sunday"],
    )


class PlanSubstituteRequest(BaseModel):
    day_number: int = Field(..., ge=1, le=7)
    meal_slot: Literal["breakfast", "lunch", "dinner", "snack"]
    item_name: str = Field(..., min_length=1)
    reason: str = Field(default="User requested substitution")


class PlanGenerateResponse(BaseModel):
    session_id: str
    plan_id: str
    profile: dict
    plan: dict
    nlp_analysis: dict | None = None


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    status_code=status.HTTP_201_CREATED,
    response_model=PlanGenerateResponse,
    summary="Generate a 7-day fitness and nutrition plan from natural language",
)
def generate_plan(
    body: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    End-to-end pipeline:
      1. Validates user_input
      2. Extracts structured profile using Gemini
      3. Creates UserSession in SQLite
      4. Generates 7-day plan using Gemini
      5. Validates plan structure (all 7 days, workout, nutrition)
      6. Saves plan linked to UserSession in SQLite
      7. Returns session_id, plan_id, profile, and plan
    """
    user_input = body.user_input.strip() if body.user_input else ""

        # ---------------------------------------------------------
    # NLP PREPROCESSING
    # ---------------------------------------------------------
    try:
        nlp_analysis = analyze_text(user_input)
        logger.info("NLP analysis: %s", nlp_analysis)
    except Exception as exc:
        logger.error("NLP analysis failed: %s", exc)

        # NLP should not break the main GenAI workflow.
        nlp_analysis = {
            "intent": "UNKNOWN",
            "intent_confidence": 0.0,
            "tokens": [],
            "keywords": [],
            "entities": {},
        }

    if not user_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_input cannot be empty.",
        )

    # Step 2: Build profile extraction prompt
    profile_prompts = build_profile_extraction_prompt(
    user_input,
    nlp_analysis
)

    # Step 3 & 4: Call Gemini and parse profile
    try:
        raw_profile_text = gemini_service.invoke(
            user_prompt=profile_prompts["user"],
            system_prompt=profile_prompts["system"],
            temperature=0.2,
            response_mime_type="application/json",
        )
    except GeminiServiceError as exc:
        logger.error("Gemini service error during profile extraction: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Profile extraction failed: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during profile extraction: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error communicating with LLM: {str(exc)}",
        ) from exc

    try:
        profile_json = parse_llm_json(raw_profile_text)
        validated_profile = validate_profile_extraction_response(profile_json)
    except LLMResponseError as exc:
        logger.error("Profile parsing/validation failed: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid profile extraction response from LLM: {exc.message}",
        ) from exc

    # Step 6: Create UserSession in SQLite
    try:
        user_session = create_user_session(db, validated_profile)
    except Exception as exc:
        logger.error("Database error while creating user session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error: unable to save user session.",
        ) from exc

    # Step 7: Build plan generation prompt using extracted profile
    plan_prompts = build_plan_generation_prompt(validated_profile)

    # Step 8, 9 & 10: Call Gemini and validate 7-day plan
    try:
        validated_plan = _invoke_validated_plan(plan_prompts, validated_profile)

    except (GeminiServiceError, LLMResponseError, Exception) as exc:
        logger.error("Plan generation/validation failed: %s. Rolling back session.", exc)
        try:
            db.delete(user_session)
            db.commit()
        except Exception as cleanup_exc:
            logger.error("Error during session rollback: %s", cleanup_exc)
            db.rollback()

        if isinstance(exc, GeminiServiceError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Plan generation failed: {exc.message}",
            ) from exc
        elif isinstance(exc, LLMResponseError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid plan response from LLM: {exc.message}",
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during plan generation: {str(exc)}",
            ) from exc

    # Step 11: Save the generated plan to the Plan table
    try:
        plan_record = save_plan(db, user_session.id, validated_plan)
    except Exception as exc:
        logger.error("Database error while saving plan: %s", exc)
        try:
            db.delete(user_session)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error: unable to save generated plan.",
        ) from exc

    # Step 12: Return clean JSON response
    return PlanGenerateResponse(
        session_id=user_session.id,
        plan_id=plan_record.id,
        profile=validated_profile,
        plan=validated_plan,
        nlp_analysis=nlp_analysis,
    )


@router.post(
    "/{plan_id}/modify",
    status_code=status.HTTP_200_OK,
    response_model=PlanGenerateResponse,
    summary="Modify an existing 7-day plan using conversational natural language",
)
def modify_plan(
    plan_id: str,
    body: PlanModifyRequest,
    db: Session = Depends(get_db),
):
    """
    Conversational plan modification workflow:
      1. Validate user_request
      2. Retrieve existing Plan record by plan_id
      3. Retrieve associated UserSession to extract permanent profile constraints
      4. Build plan modification prompt using existing plan & user profile
      5. Invoke Gemini to modify the plan
      6. Parse and validate the returned modified plan JSON
      7. Save the modified plan as a new Plan record under the same UserSession
      8. Return session_id, new plan_id, profile, and modified plan
    """
    user_request = body.user_request.strip() if body.user_request else ""
    if not user_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_request cannot be empty.",
        )

    # 1. Retrieve existing plan
    plan_record = get_plan_by_id(db, plan_id)
    if plan_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found.",
        )

    # 2. Retrieve associated user session
    user_session = get_user_session(db, plan_record.session_id)
    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated UserSession '{plan_record.session_id}' not found.",
        )

    # 3. Parse existing plan JSON
    try:
        existing_plan_data = json.loads(plan_record.plan_content)
    except Exception as exc:
        logger.error("Failed to parse existing plan JSON from database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load existing plan data from database.",
        ) from exc

    # 4. Extract profile dictionary
    profile_dict = {
        "age": user_session.age,
        "gender": user_session.gender,
        "height": user_session.height,
        "weight": user_session.weight,
        "fitness_goal": user_session.fitness_goal,
        "fitness_level": user_session.fitness_level,
        "available_time": user_session.available_time,
        "equipment": user_session.equipment,
        "food_preference": user_session.food_preference,
        "food_restrictions": user_session.food_restrictions,
        "budget": user_session.budget,
    }

    # 5. Build prompt
    prompt_data = build_plan_modification_prompt(
        user_request=user_request,
        existing_plan=existing_plan_data,
        profile=profile_dict,
        current_day=body.current_day,
    )

    # 6. Invoke Gemini
    try:
        validated_modified_plan = _invoke_validated_modification(
            prompt_data, existing_plan_data, profile_dict
        )
    except GeminiServiceError as exc:
        logger.error("Gemini service error during plan modification: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Plan modification failed: {exc.message}",
        ) from exc
    except LLMResponseError as exc:
        logger.error("Plan modification response validation failed: %s", exc.message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid modified plan response from LLM: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during plan modification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error communicating with LLM: {str(exc)}",
        ) from exc

    # 7. Persist the modified plan as a new Plan record for this session
    try:
        new_plan_record = save_plan(db, user_session.id, validated_modified_plan)
    except Exception as exc:
        logger.error("Database error while saving modified plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error: unable to save modified plan.",
        ) from exc

    # 9. Return response
    return PlanGenerateResponse(
        session_id=user_session.id,
        plan_id=new_plan_record.id,
        profile=profile_dict,
        plan=validated_modified_plan,
    )


@router.post(
    "/{plan_id}/substitute",
    status_code=status.HTTP_200_OK,
    response_model=PlanGenerateResponse,
    summary="Replace a food item and recalculate daily nutrition estimates",
)
def substitute_plan_food(
    plan_id: str,
    body: PlanSubstituteRequest,
    db: Session = Depends(get_db),
):
    plan_record = get_plan_by_id(db, plan_id)
    if plan_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{plan_id}' not found.")

    user_session = get_user_session(db, plan_record.session_id)
    if user_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated UserSession '{plan_record.session_id}' not found.",
        )

    try:
        plan_data = json.loads(plan_record.plan_content)
    except Exception as exc:
        logger.error("Failed to parse existing plan JSON from database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load existing plan data from database.",
        ) from exc

    profile_dict = {
        "age": user_session.age,
        "gender": user_session.gender,
        "height": user_session.height,
        "weight": user_session.weight,
        "fitness_goal": user_session.fitness_goal,
        "fitness_level": user_session.fitness_level,
        "available_time": user_session.available_time,
        "equipment": user_session.equipment,
        "food_preference": user_session.food_preference,
        "food_restrictions": user_session.food_restrictions,
        "budget": user_session.budget,
    }
    day = next(
        (item for item in plan_data.get("days", []) if item.get("day_number") == body.day_number),
        None,
    )
    if day is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Day {body.day_number} not found.")

    nutrition = day.get("nutrition") or {}
    current_meal = nutrition.get(body.meal_slot)
    if not isinstance(current_meal, str) or body.item_name.lower() not in current_meal.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{body.item_name}' was not found in day {body.day_number}'s {body.meal_slot} meal.",
        )
    current_nutrition = (nutrition.get("meal_nutrition") or {}).get(body.meal_slot)
    if not isinstance(current_nutrition, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This saved plan has no per-meal nutrition estimates; generate a new plan before substituting meals.",
        )

    prompts = build_substitution_prompt(
        item_type="food",
        item_name=body.item_name,
        profile=profile_dict,
        reason=body.reason,
        meal_slot=body.meal_slot,
        current_meal=current_meal,
        current_nutrition=current_nutrition,
    )
    try:
        raw_response = gemini_service.invoke(
            user_prompt=prompts["user"],
            system_prompt=prompts["system"],
            temperature=0.2,
            response_mime_type="application/json",
        )
        replacement = validate_substitution_response(parse_llm_json(raw_response))
        plan_data = apply_food_substitution(
            plan_data,
            body.day_number,
            body.meal_slot,
            replacement,
            profile_dict,
        )
    except (GeminiServiceError, LLMResponseError, NutritionValidationError) as exc:
        message = exc.message if isinstance(exc, GeminiServiceError) else str(exc)
        logger.error("Food substitution failed: %s", message)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Food substitution failed validation: {message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during food substitution: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during food substitution.",
        ) from exc

    plan_data["modification_summary"] = (
        f"Replaced {body.item_name} in {body.meal_slot} on day {body.day_number} "
        f"with {replacement['replacement_name']}; daily nutrition totals were recalculated."
    )
    try:
        new_plan_record = save_plan(db, user_session.id, plan_data)
    except Exception as exc:
        logger.error("Database error while saving substituted plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error: unable to save substituted plan.",
        ) from exc

    return PlanGenerateResponse(
        session_id=user_session.id,
        plan_id=new_plan_record.id,
        profile=profile_dict,
        plan=plan_data,
    )
