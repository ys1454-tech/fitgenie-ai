"""
plan_generation.py — Prompt template for generating personalized 7-day fitness
and nutrition plans based on structured user profiles.
"""

PLAN_GENERATION_SYSTEM_PROMPT = """You are FitGenie AI, an expert fitness trainer and certified sports nutritionist.
Your mission is to generate practical, highly personalized, and safe 7-day fitness and meal plans based strictly on the user's personal profile, goals, and constraints.

Always output your response in strict, valid JSON format matching the specified schema.
Do not include conversational preamble, postscript explanations, or markdown fences outside the JSON.
"""

PLAN_GENERATION_USER_PROMPT = """### ROLE
You are an expert fitness coach and sports nutritionist creating a tailored 7-day fitness and nutrition program.

### USER CONTEXT
User Profile:
- Age: {age}
- Gender: {gender}
- Height: {height} cm
- Weight: {weight} kg
- Fitness Goal: {fitness_goal}
- Fitness Level: {fitness_level}
- Available Workout Time: {available_time} minutes/day
- Available Equipment: {equipment}
- Dietary Preference: {food_preference}
- Dietary Restrictions / Allergies: {food_restrictions}
- Weekly Meal Budget: {budget}

### TASK
Generate a comprehensive, balanced 7-day workout and nutrition plan tailored specifically to the user's profile and constraints.

### CONSTRAINTS
1. Daily workout duration MUST NOT exceed the user's available time of {available_time} minutes.
2. Exercises MUST ONLY utilize the available equipment: {equipment}. If none is available, use bodyweight exercises only.
3. Workout intensity and volume MUST align with the user's fitness level ({fitness_level}) and goal ({fitness_goal}). Include rest or active recovery days if appropriate for their level.
4. All meals (breakfast, lunch, dinner) MUST strictly comply with dietary preferences ({food_preference}) and avoid all restricted ingredients ({food_restrictions}).
5. If a budget is specified ({budget}), recommend affordable, accessible everyday ingredients.
6. Provide specific, practical exercise names with sets and reps (or duration in seconds/minutes).
7. Provide realistic, easy-to-prepare meal suggestions with brief portion/ingredient guidance.

### EXPECTED OUTPUT FORMAT
Respond ONLY with a JSON object following this exact structure:
{{
  "plan_title": "7-Day Personalized Fitness & Nutrition Plan",
  "summary": "Brief overview of the weekly strategy and approach tailored to the user",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Monday",
      "workout": {{
        "title": "Workout session name (or Rest & Recovery)",
        "duration_minutes": {available_time},
        "focus_area": "Target muscle groups or fitness attribute",
        "exercises": [
          {{
            "name": "Exercise name",
            "sets": 3,
            "reps_or_duration": "10-12 reps",
            "rest_seconds": 60,
            "instructions": "Key form cue or technique tip"
          }}
        ]
      }},
      "nutrition": {{
        "breakfast": "Meal description with main ingredients and portion size",
        "lunch": "Meal description with main ingredients and portion size",
        "dinner": "Meal description with main ingredients and portion size",
        "snack": "Optional healthy snack recommendation",
        "daily_calories_target": "Estimated daily calorie goal, e.g. ~2000 kcal"
      }},
      "daily_notes": "Important hydration, sleep, warm-up, or recovery reminders for this day"
    }}
  ]
}}

Ensure all 7 days (day_number 1 through 7) are included in the 'days' array.
"""


def build_plan_generation_prompt(profile: dict) -> dict:
    """
    Build the system and user prompts for 7-day plan generation.

    Args:
        profile: Dictionary containing user profile fields.

    Returns:
        dict with 'system' and 'user' prompt strings.
    """
    user_prompt = PLAN_GENERATION_USER_PROMPT.format(
        age=profile.get("age") or "Not specified",
        gender=profile.get("gender") or "Not specified",
        height=profile.get("height") or "Not specified",
        weight=profile.get("weight") or "Not specified",
        fitness_goal=profile.get("fitness_goal") or "General Fitness",
        fitness_level=profile.get("fitness_level") or "Beginner",
        available_time=profile.get("available_time") or 30,
        equipment=profile.get("equipment") or "Bodyweight / None",
        food_preference=profile.get("food_preference") or "No specific preference",
        food_restrictions=profile.get("food_restrictions") or "None",
        budget=profile.get("budget") or "Standard / Flexible",
    )

    return {
        "system": PLAN_GENERATION_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
