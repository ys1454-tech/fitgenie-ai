"""
plan_modification.py — Prompt template for conversational plan modifications.
Allows users to adjust their 7-day plan using natural-language requests.
"""

import json

PLAN_MODIFICATION_SYSTEM_PROMPT = """You are FitGenie AI, an adaptive fitness and nutrition coach.
Your task is to modify an existing 7-day fitness and meal plan based on a user's specific follow-up request, while maintaining overall program balance and respecting the user's permanent profile constraints.

Return only a compact JSON patch for the days and fields that need to change. The backend preserves all omitted days and fields.
Do not include conversational preamble, explanations, or markdown fences outside the JSON.
"""

PLAN_MODIFICATION_USER_PROMPT = """### USER PROFILE & PERMANENT CONSTRAINTS
- Fitness Goal: {fitness_goal}
- Fitness Level: {fitness_level}
- Standard Available Time: {available_time} minutes
- Equipment: {equipment}
- Dietary Preference: {food_preference}
- Dietary Restrictions: {food_restrictions}
- Current Day Reference: {current_day} (if user mentions 'today' or 'tomorrow', map accordingly)

### EXISTING 7-DAY PLAN
```json
{existing_plan_json}
```

### USER'S MODIFICATION REQUEST
"{user_request}"

### TASK & INSTRUCTIONS
1. Analyze the user's modification request (e.g. reduced time for a specific day, injury adaptation, meal change, schedule swap).
2. Apply the requested changes to every relevant day. Include a separate day update for each affected day; do not omit a requested day.
3. Return only changed fields. Never repeat unchanged workouts, meals, or days.
4. In each modified day's 'daily_notes', mention the applied modification and why.
5. Maintain strict compliance with the user's permanent constraints (allergies, available equipment, etc.).
6. For every changed meal description, return new numeric estimates for that meal in 'nutrition.meal_nutrition'. Do not change estimates for untouched meals.
7. Use the existing portion sizes when estimating; these values are estimates, not verified nutrition facts. Do not return daily totals; the backend calculates them.

### EXPECTED OUTPUT FORMAT
Return a JSON object with this exact structure. Include only affected days and changed fields:
{{
  "modification_summary": "Brief summary of what specific changes were applied in response to the user's request",
  "day_updates": [
    {{
      "day_number": 1,
      "nutrition": {{
        "lunch": "Changed meal description with portions",
        "meal_nutrition": {{
          "lunch": {{"calories_kcal": 600, "protein_g": 35, "carbs_g": 70, "fat_g": 20}}
        }}
      }},
      "daily_notes": "Notes about this modification"
    }}
  ]
}}
"""


def build_plan_modification_prompt(
    user_request: str,
    existing_plan: dict | str,
    profile: dict,
    current_day: str | None = None,
) -> dict:
    """
    Build the system and user prompts for conversational plan modification.

    Args:
        user_request: The user's conversational modification message.
        existing_plan: The current plan as a dict or JSON string.
        profile: The user profile dictionary.
        current_day: Optional current day of the week (e.g. Sunday) to resolve 'today'.

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
        current_day=current_day or "Not specified",
        existing_plan_json=plan_str,
        user_request=user_request.strip(),
    )

    return {
        "system": PLAN_MODIFICATION_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
