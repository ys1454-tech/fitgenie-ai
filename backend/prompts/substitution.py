"""
substitution.py — Prompt template for individual exercise or food item substitutions.
Allows users to swap a specific item while preserving workout/nutrition continuity.
"""


import json

SUBSTITUTION_SYSTEM_PROMPT = """You are FitGenie AI's substitution assistant.
Your task is to provide a single, targeted replacement for a specific exercise or food item from the user's plan.

Requirements:

Output ONLY a valid JSON object matching the requested schema. No conversational filler or external text.
"""

SUBSTITUTION_USER_PROMPT = """### USER PROFILE & CONSTRAINTS
- Fitness Goal: {fitness_goal}
- Fitness Level: {fitness_level}
- Available Equipment: {equipment}
- Dietary Preference: {food_preference}
- Dietary Restrictions: {food_restrictions}

### SUBSTITUTION REQUEST
- Item Type: {item_type} (exercise OR food)
- Item to Replace: "{item_name}"
- Meal Slot: {meal_slot}
- Existing Meal Description: "{current_meal}"
- Existing Meal Nutrition Estimate: {current_nutrition_json}
- Reason / Context (if any): "{reason}"

### TASK
Provide an optimal, direct alternative to "{item_name}" that satisfies all user constraints.

### EXPECTED OUTPUT FORMAT
Return a JSON object with this exact structure:
{{
  "item_type": "{item_type}",
  "original_item": "{item_name}",
  "replacement_name": "Name of the alternative exercise or meal item",
    "meal_description": "Full replacement meal description with ingredients and portions",
    "nutrition": {{"calories_kcal": 400, "protein_g": 20, "carbs_g": 50, "fat_g": 10}},
  "reason_for_choice": "Explanation of why this replacement fits the user's muscle group/nutritional need and constraints"
}}
"""


def build_substitution_prompt(
    item_type: str,
    item_name: str,
    profile: dict,
    reason: str = "User requested substitution",
    meal_slot: str = "Not specified",
    current_meal: str = "Not specified",
    current_nutrition: dict | None = None,
) -> dict:
    """
    Build the system and user prompts for substituting an exercise or food item.

    Args:
        item_type: "exercise" or "food".
        item_name: Name of the item to be replaced.
        profile: The user profile dictionary.
        reason: Optional user rationale (e.g. "knee pain", "don't like taste").

    Returns:
        dict with 'system' and 'user' prompt strings.
    """
    user_prompt = SUBSTITUTION_USER_PROMPT.format(
        fitness_goal=profile.get("fitness_goal") or "General Fitness",
        fitness_level=profile.get("fitness_level") or "Beginner",
        equipment=profile.get("equipment") or "Bodyweight",
        food_preference=profile.get("food_preference") or "Standard",
        food_restrictions=profile.get("food_restrictions") or "None",
        item_type=item_type.strip().lower(),
        item_name=item_name.strip(),
        meal_slot=meal_slot,
        current_meal=current_meal,
        current_nutrition_json=json.dumps(current_nutrition or {}, ensure_ascii=False),
        reason=reason.strip(),
    )

    return {
        "system": SUBSTITUTION_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
