"""
plan_modification.py — Prompt template for conversational plan modifications.
Allows users to adjust their 7-day plan using natural-language requests.
"""

import json

PLAN_MODIFICATION_SYSTEM_PROMPT = """You are FitGenie AI, an adaptive fitness and nutrition coach.
Your task is to modify an existing 7-day fitness and meal plan based on a user's specific follow-up request, while maintaining overall program balance and respecting the user's permanent profile constraints.

Always return the full updated 7-day plan in strict JSON format.
Do not include conversational preamble, explanations, or markdown fences outside the JSON.
"""

PLAN_MODIFICATION_USER_PROMPT = """### USER PROFILE & PERMANENT CONSTRAINTS
- Fitness Goal: {fitness_goal}
- Fitness Level: {fitness_level}
- Standard Available Time: {available_time} minutes
- Equipment: {equipment}
- Dietary Preference: {food_preference}
- Dietary Restrictions: {food_restrictions}

### EXISTING 7-DAY PLAN
```json
{existing_plan_json}
```

### USER'S MODIFICATION REQUEST
"{user_request}"

### TASK & INSTRUCTIONS
1. Analyze the user's modification request (e.g. reduced time for a specific day, injury adaptation, meal change, schedule swap).
2. Apply the requested changes to the relevant day(s) while leaving the rest of the plan cohesive and intact.
3. In each modified day's 'daily_notes', explicitly mention what modification was applied and why.
4. Maintain strict compliance with the user's permanent constraints (allergies, available equipment, etc.).

### EXPECTED OUTPUT FORMAT
Return a JSON object with this exact structure:
{{
  "plan_title": "Updated 7-Day Personalized Fitness & Nutrition Plan",
  "modification_summary": "Brief summary of what specific changes were applied in response to the user's request",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Monday",
      "workout": {{
        "title": "Workout session title",
        "duration_minutes": 30,
        "focus_area": "Target muscle groups or focus",
        "exercises": [
          {{
            "name": "Exercise name",
            "sets": 3,
            "reps_or_duration": "10-12 reps",
            "rest_seconds": 60,
            "instructions": "Form cues or coaching notes"
          }}
        ]
      }},
      "nutrition": {{
        "breakfast": "Meal description",
        "lunch": "Meal description",
        "dinner": "Meal description",
        "snack": "Snack recommendation",
        "daily_calories_target": "Estimated calories"
      }},
      "daily_notes": "Notes including mention of any applied modifications"
    }}
  ]
}}
"""


def build_plan_modification_prompt(
    user_request: str,
    existing_plan: dict | str,
    profile: dict,
) -> dict:
    """
    Build the system and user prompts for conversational plan modification.

    Args:
        user_request: The user's conversational modification message.
        existing_plan: The current plan as a dict or JSON string.
        profile: The user profile dictionary.

    Returns:
        dict with 'system' and 'user' prompt strings.
    """
    if isinstance(existing_plan, dict):
        plan_str = json.dumps(existing_plan, indent=2, ensure_ascii=False)
    else:
        plan_str = str(existing_plan)

    user_prompt = PLAN_MODIFICATION_USER_PROMPT.format(
        fitness_goal=profile.get("fitness_goal") or "General Fitness",
        fitness_level=profile.get("fitness_level") or "Beginner",
        available_time=profile.get("available_time") or 30,
        equipment=profile.get("equipment") or "Bodyweight",
        food_preference=profile.get("food_preference") or "Standard",
        food_restrictions=profile.get("food_restrictions") or "None",
        existing_plan_json=plan_str,
        user_request=user_request.strip(),
    )

    return {
        "system": PLAN_MODIFICATION_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
