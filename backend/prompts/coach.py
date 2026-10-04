"""
coach.py — Prompt template for the real-time aware, strictly question-focused FitGenie AI Coach.

This prompt handles conversational and informational questions about the user's
plan and profile (e.g. "What should I eat now?", "What is my breakfast today?",
"What is my initial weight?", "Why is protein important?").

CORE DIRECTIVE:
Answer ONLY what the user asked. Never dump unrequested meals, workouts, or profile facts.
"""

import json

COACH_SYSTEM_PROMPT = """You are FitGenie AI Coach, a highly focused, professional, and knowledgeable personal fitness and nutrition assistant.

CORE DIRECTIVE:
Answer ONLY what the user specifically asked. Be direct, concise, and focused.
DO NOT volunteer unrequested information, unrequested meals, unrequested workouts, or unrequested advice.

STRICT CONVERSATIONAL RULES:
1. ANSWER SCOPE:
   - If the user asks about a single meal (e.g. "What is my breakfast today?"), answer ONLY that meal. Do NOT list lunch, dinner, snack, or workouts.
   - If the user asks about lunch, answer ONLY lunch.
   - If the user asks about dinner, answer ONLY dinner.
   - If the user asks about snacks, answer ONLY snacks.
   - If the user asks about today's workout (e.g. "What is my workout today?"), answer ONLY today's workout (title, duration, focus, exercises). Do NOT mention meals or nutrition.
   - If the user asks about workout duration (e.g. "How long is today's workout?"), state ONLY the duration and title.
   - If the user asks "What should I eat now?", identify ONLY the single most relevant meal based on current local time. Do NOT mention the next meal or future meals. Do NOT add unrelated workouts or profile details.
   - If the user asks about tomorrow's meals (e.g. "What am I eating tomorrow?"), answer ONLY tomorrow's meals. Do NOT discuss today or workouts.
   - If the user asks about their profile (e.g. weight, height, age, goal, budget, equipment), answer ONLY that specific attribute.
   - If the user greets (e.g. "Hello", "Hi"), give a friendly 1-sentence greeting. Do NOT list any plan details or profile metrics.
   - If the user says "Thank you", give a polite 1-sentence acknowledgment. Do NOT list any plan details.
   - If the user asks a general fitness/nutrition or educational question (e.g. "Why is protein important?"), answer that educational question concisely and accurately without referencing or dumping personal schedules, meals, workouts, or profile facts.

2. CONTEXT IS A REFERENCE, NOT A SCRIPT:
   - You are provided with real-time context (date, day, time, today's plan, tomorrow's plan, profile).
   - Use this context ONLY when it is directly relevant to answering the user's question.
   - NEVER start responses with "Since today is Sunday..." or "It's 2:00 PM..." unless the question specifically requires knowing the day or time (such as "What should I eat now?").
   - NEVER dump the entire plan or profile when asked a specific question.
   - NEVER append unrequested motivational quotes, unsolicited coaching advice, or future meal previews.

3. ZERO HALLUCINATION:
   - When quoting foods or workouts from the user's plan, use the EXACT names and descriptions from the provided plan.
   - Never invent food, workouts, or profile metrics.
   - If a requested piece of information is not in the context, state simply and clearly that it is not available.

4. TONE:
   - Direct, friendly, and natural.
   - No robotic preambles ("Acknowledged user request...").
   - Return plain text only (do NOT return JSON).
"""

COACH_USER_PROMPT = """### CONTEXT DATA (Use ONLY if relevant to the question)
Current Real-Time Context:
- Current Date: {current_date}
- Current Day of Week: {current_day}
- Current Local Time: {current_time}
- Today in Plan: Day {today_day_number} ({current_day})
- Tomorrow in Plan: Day {tomorrow_day_number} ({tomorrow_day})

User Profile:
- Age: {age}
- Gender: {gender}
- Height: {height}
- Weight: {weight}
- Fitness Goal: {fitness_goal}
- Fitness Level: {fitness_level}
- Standard Available Time: {available_time} minutes
- Equipment: {equipment}
- Dietary Preference: {food_preference}
- Dietary Restrictions: {food_restrictions}
- Budget: {budget}

Today's Plan — Day {today_day_number} ({current_day}):
- Workout Title: {today_workout_title}
- Workout Duration: {today_workout_duration} minutes
- Workout Focus: {today_workout_focus}
- Exercises:
{today_exercises}
- Breakfast: {today_breakfast}
- Lunch: {today_lunch}
- Snack: {today_snack}
- Dinner: {today_dinner}
- Daily Calories Target: {today_calories}
- Daily Notes: {today_notes}

Tomorrow's Plan — Day {tomorrow_day_number} ({tomorrow_day}):
- Workout Title: {tomorrow_workout_title}
- Workout Duration: {tomorrow_workout_duration} minutes
- Workout Focus: {tomorrow_workout_focus}
- Breakfast: {tomorrow_breakfast}
- Lunch: {tomorrow_lunch}
- Snack: {tomorrow_snack}
- Dinner: {tomorrow_dinner}
- Daily Calories Target: {tomorrow_calories}

### USER'S QUESTION
"{user_request}"

### INSTRUCTION
Answer ONLY what the user asked above. Do not include unrequested meals, workouts, dates, or profile attributes. Keep the answer direct and concise.
"""

COACH_EDUCATIONAL_USER_PROMPT = """### USER'S QUESTION
"{user_request}"

### INSTRUCTION
Provide a clear, accurate, and concise answer to the educational/fitness question above.
Do NOT reference or invent any personal schedules, specific daily meal plans, or workout days.
Answer ONLY the specific question asked.
"""

COACH_FOOD_ALTERNATIVE_SYSTEM_PROMPT = """You are FitGenie AI Coach, an adaptive personal fitness and nutrition assistant.

CORE TASK:
The user indicates that their planned food or ingredients are unavailable, or they are asking for a practical dietary alternative.
Suggest practical, realistic, and healthy alternatives for their meal based on their profile.

STRICT CONVERSATIONAL RULES:
1. Identify the relevant planned meal and acknowledge that it is unavailable or that an alternative is needed.
2. Suggest 2-3 practical, common alternative food options that provide similar nutritional value.
3. STRICT COMPLIANCE WITH USER PROFILE:
   - Food Preference: Must strictly respect the user's dietary preference (e.g. Indian Vegetarian, Vegan, Non-Vegetarian). NEVER suggest meat, poultry, fish, or eggs to a vegetarian unless specified in their profile.
   - Dietary Restrictions: Strictly avoid any foods or allergens listed in their dietary restrictions.
   - Fitness Goal: Keep calorie and macronutrient balance aligned with their goal (e.g. weight loss, muscle gain).
   - Budget: Suggest easily accessible, budget-friendly ingredients.
   - Quick / Uncooked Options: If the user states they have nothing cooked or cannot cook right now, suggest quick, ready-to-eat or minimal-prep options (such as curd with fruit, a simple paneer or peanut butter sandwich, or oats with milk/nuts) that comply with their dietary preference.
4. DO NOT recommend the original unavailable food.
5. DO NOT dump today's entire meal plan or tomorrow's meals.
6. DO NOT mention workouts, exercises, or unrelated profile attributes.
7. DO NOT invent medical claims, exact calorie counts, or clock times.
8. Tone: Concise, reassuring, direct, and helpful (2-4 sentences). Return plain text only.
"""

COACH_FOOD_ALTERNATIVE_USER_PROMPT = """### CONTEXT DATA
- Current Day: {current_day}
- Current Local Time: {current_time}
- Relevant Meal: {relevant_meal_name}
- Planned Food in Today's Plan: {planned_food}
- Daily Calories Target: {daily_calories_target}

User Profile Constraints:
- Dietary Preference: {food_preference}
- Dietary Restrictions: {food_restrictions}
- Fitness Goal: {fitness_goal}
- Monthly Budget: {budget}

### USER'S REQUEST
"{user_request}"

### INSTRUCTION
Suggest practical and healthy alternatives for the user's meal above.
Strictly adhere to the user's dietary preference ({food_preference}), restrictions ({food_restrictions}), and fitness goal ({fitness_goal}).
Keep the response concise, direct, and focused only on the food alternatives. Do not mention workouts or other meals.
"""


def is_food_alternative_request(user_request: str) -> bool:
    """
    Detect whether the user is indicating that their planned food or ingredients
    are unavailable, or requesting a dietary alternative/substitution.
    """
    req = user_request.lower().strip()

    # Explicit alternative/substitution markers
    if any(k in req for k in [
        "instead", "alternative", "substitute", "substitutes",
        "other than", "swap for", "swap with"
    ]):
        return True

    # Unavailability markers
    unavail_markers = [
        "don't have", "dont have", "do not have",
        "can't get", "cant get", "cannot get",
        "ran out", "out of", "not available", "is not available",
        "nothing cooked", "not cooked", "no cooked", "no food"
    ]
    food_markers = [
        "food", "meal", "lunch", "breakfast", "dinner", "snack",
        "eat", "eating", "cooked", "ingredients", "diet", "plan",
        "rice", "dal", "roti", "bread", "paneer", "oats", "milk", "eggs", "curry"
    ]

    for u in unavail_markers:
        if u in req:
            # Check if it relates to food and not gym equipment/workouts
            if any(f in req for f in food_markers) and not any(w in req for w in ["dumbbell", "equipment", "workout", "exercise"]):
                return True

    return False


def get_relevant_meal_info(user_request: str, today_plan: dict, current_time: str) -> tuple[str, str]:
    """
    Determine which meal from today's plan is being referred to (or currently scheduled).
    Returns (meal_name, planned_food).
    """
    today_nutrition = (today_plan or {}).get("nutrition") or {}
    req = user_request.lower()

    if "breakfast" in req:
        return "Breakfast", today_nutrition.get("breakfast") or "Not specified"
    elif "lunch" in req:
        return "Lunch", today_nutrition.get("lunch") or "Not specified"
    elif "dinner" in req or "supper" in req:
        return "Dinner", today_nutrition.get("dinner") or "Not specified"
    elif "snack" in req:
        return "Snack", today_nutrition.get("snack") or "Not specified"

    # Fall back to time-based meal determination
    import re
    hour = 12
    m = re.search(r"(\d{1,2}):", current_time or "")
    if m:
        try:
            hour = int(m.group(1))
        except ValueError:
            pass

    if 5 <= hour < 11:
        return "Breakfast", today_nutrition.get("breakfast") or "Not specified"
    elif 11 <= hour < 16:
        return "Lunch", today_nutrition.get("lunch") or "Not specified"
    elif 16 <= hour < 19:
        return "Snack", today_nutrition.get("snack") or "Not specified"
    else:
        return "Dinner", today_nutrition.get("dinner") or "Not specified"


def build_coach_prompt(
    user_request: str,
    current_date: str,
    current_day: str,
    current_time: str,
    today_plan: dict,
    tomorrow_plan: dict | None,
    profile: dict,
) -> dict:
    """
    Build the system and user prompts for the question-focused AI Coach.

    Args:
        user_request:       The user's conversational question.
        current_date:       ISO date string e.g. "2026-10-04"
        current_day:        Day name e.g. "Sunday"
        current_time:       Time string e.g. "13:31"
        today_plan:         The day dict from the plan (day_number, day_name, workout, nutrition, daily_notes)
        tomorrow_plan:      The day dict for tomorrow (optional)
        profile:            The user profile dictionary.

    Returns:
        dict with 'system' and 'user' prompt strings.
    """
    req_lower = user_request.lower().strip()

    # 1. Food Alternative / Unavailable food branch
    if is_food_alternative_request(user_request):
        meal_name, planned_food = get_relevant_meal_info(user_request, today_plan, current_time)
        budget_val = profile.get("budget")
        budget_str = f"₹{int(budget_val) if isinstance(budget_val, (int, float)) and budget_val == int(budget_val) else budget_val}/month" if budget_val is not None else "Standard"
        daily_cals = (today_plan.get("nutrition") or {}).get("daily_calories_target") or "Not specified"

        user_prompt = COACH_FOOD_ALTERNATIVE_USER_PROMPT.format(
            current_day=current_day,
            current_time=current_time,
            relevant_meal_name=meal_name,
            planned_food=planned_food,
            daily_calories_target=daily_cals,
            food_preference=profile.get("food_preference") or "Standard",
            food_restrictions=profile.get("food_restrictions") or "None",
            fitness_goal=profile.get("fitness_goal") or "General Fitness",
            budget=budget_str,
            user_request=user_request.strip(),
        )
        return {
            "system": COACH_FOOD_ALTERNATIVE_SYSTEM_PROMPT.strip(),
            "user": user_prompt.strip(),
        }

    # 2. Educational / General fitness & nutrition branch
    is_educational = (
        any(req_lower.startswith(prefix) for prefix in [
            "why is", "why are", "why does", "what is protein", "what are protein",
            "what is creatine", "explain", "how does protein", "what are macros",
            "why should i drink water", "why is sleep", "tell me about"
        ])
        and not any(k in req_lower for k in ["today", "tomorrow", "my plan", "my workout", "my breakfast", "my lunch", "my dinner", "my snack", "my diet"])
    )

    if is_educational:
        return {
            "system": COACH_SYSTEM_PROMPT.strip(),
            "user": COACH_EDUCATIONAL_USER_PROMPT.format(user_request=user_request.strip()).strip(),
        }

    today_workout = today_plan.get("workout") or {}
    today_nutrition = today_plan.get("nutrition") or {}
    exercises_list = today_workout.get("exercises") or []
    if exercises_list:
        exercise_lines = [
            f"  * {ex.get('name', 'Exercise')} ({ex.get('sets', '')} sets × {ex.get('reps_or_duration', '')})"
            for ex in exercises_list
        ]
        today_exercises = "\n".join(exercise_lines)
    else:
        today_exercises = "  * Rest & Recovery"

    tom_plan = tomorrow_plan or {}
    tomorrow_workout = tom_plan.get("workout") or {}
    tomorrow_nutrition = tom_plan.get("nutrition") or {}

    today_day_num = today_plan.get("day_number", "—")
    tomorrow_day_num = tom_plan.get("day_number", "—")
    tomorrow_day_name = tom_plan.get("day_name", "Tomorrow")

    age_val = profile.get("age")
    height_val = profile.get("height")
    weight_val = profile.get("weight")
    budget_val = profile.get("budget")

    user_prompt = COACH_USER_PROMPT.format(
        current_date=current_date,
        current_day=current_day,
        current_time=current_time,
        today_day_number=today_day_num,
        tomorrow_day_number=tomorrow_day_num,
        tomorrow_day=tomorrow_day_name,
        age=f"{age_val} years" if age_val is not None else "Not specified",
        gender=profile.get("gender") or "Not specified",
        height=f"{height_val} cm" if height_val is not None else "Not specified",
        weight=f"{weight_val} kg" if weight_val is not None else "Not specified",
        fitness_goal=profile.get("fitness_goal") or "General Fitness",
        fitness_level=profile.get("fitness_level") or "Beginner",
        available_time=profile.get("available_time") or 30,
        equipment=profile.get("equipment") or "Bodyweight",
        food_preference=profile.get("food_preference") or "Standard",
        food_restrictions=profile.get("food_restrictions") or "None",
        budget=f"₹{budget_val}/month" if budget_val is not None else "Not specified",
        today_workout_title=today_workout.get("title") or "Rest Day",
        today_workout_duration=today_workout.get("duration_minutes") or 0,
        today_workout_focus=today_workout.get("focus_area") or "Rest & Recovery",
        today_exercises=today_exercises,
        today_breakfast=today_nutrition.get("breakfast") or "Not specified",
        today_lunch=today_nutrition.get("lunch") or "Not specified",
        today_snack=today_nutrition.get("snack") or "Not specified",
        today_dinner=today_nutrition.get("dinner") or "Not specified",
        today_calories=today_nutrition.get("daily_calories_target") or "Not specified",
        today_notes=today_plan.get("daily_notes") or "Stay hydrated and stick to your plan.",
        tomorrow_workout_title=tomorrow_workout.get("title") or "Rest Day",
        tomorrow_workout_duration=tomorrow_workout.get("duration_minutes") or 0,
        tomorrow_workout_focus=tomorrow_workout.get("focus_area") or "Rest & Recovery",
        tomorrow_breakfast=tomorrow_nutrition.get("breakfast") or "Not specified",
        tomorrow_lunch=tomorrow_nutrition.get("lunch") or "Not specified",
        tomorrow_snack=tomorrow_nutrition.get("snack") or "Not specified",
        tomorrow_dinner=tomorrow_nutrition.get("dinner") or "Not specified",
        tomorrow_calories=tomorrow_nutrition.get("daily_calories_target") or "Not specified",
        user_request=user_request.strip(),
    )

    return {
        "system": COACH_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
