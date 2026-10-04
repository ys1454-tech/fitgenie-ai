"""
substitution.py — Prompt template for individual exercise or food item substitutions.
Allows users to swap a specific item while preserving workout/nutrition continuity.
"""

SUBSTITUTION_SYSTEM_PROMPT = """You are FitGenie AI's substitution assistant.
Your task is to provide a single, targeted replacement for a specific exercise or food item from the user's plan.

Requirements:
- For exercise substitutions: Target the same primary muscle group, match the user's fitness level, and use ONLY their available equipment.
- For food substitutions: Provide an equivalent nutritional role (e.g. carb source, lean protein), strictly match dietary preferences, and respect all food restrictions.

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
- Reason / Context (if any): "{reason}"

### TASK
Provide an optimal, direct alternative to "{item_name}" that satisfies all user constraints.

### EXPECTED OUTPUT FORMAT
Return a JSON object with this exact structure:
{{
  "item_type": "{item_type}",
  "original_item": "{item_name}",
  "replacement_name": "Name of the alternative exercise or meal item",
  "details": {{
    "sets": <number or null, for exercise>,
    "reps_or_duration": "<string or null, e.g. '10-12 reps' or '45 seconds'>",
    "rest_seconds": <number or null>,
    "instructions_or_recipe": "Brief form coaching or simple preparation tips for this replacement"
  }},
  "reason_for_choice": "Explanation of why this replacement fits the user's muscle group/nutritional need and constraints"
}}
"""


def build_substitution_prompt(
    item_type: str,
    item_name: str,
    profile: dict,
    reason: str = "User requested substitution",
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
        reason=reason.strip(),
    )

    return {
        "system": SUBSTITUTION_SYSTEM_PROMPT.strip(),
        "user": user_prompt.strip(),
    }
