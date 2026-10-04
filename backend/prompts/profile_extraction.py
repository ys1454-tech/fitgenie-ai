"""
profile_extraction.py — Prompt template for extracting structured user profiles
from free-form natural language input.
"""

PROFILE_EXTRACTION_SYSTEM_PROMPT = """You are FitGenie AI's profile extraction assistant.
Your task is to analyze natural-language descriptions provided by users and extract their fitness and nutrition profile into a strict JSON object.

Extract only information that is explicitly stated or can be directly inferred. If a field is not mentioned, set its value to null.
Respond ONLY with valid JSON. Do not include markdown code fences, greetings, or conversational commentary.
"""

PROFILE_EXTRACTION_USER_PROMPT = """Extract the user profile from the following description:

"{user_input}"

Return a JSON object matching this exact schema:
{{
  "age": <integer or null>,
  "gender": <string or null, e.g. "Male", "Female", "Other">,
  "height": <float in cm or null>,
  "weight": <float in kg or null>,
  "fitness_goal": <string or null, e.g. "Weight Loss", "Muscle Gain", "Endurance", "General Fitness">,
  "fitness_level": <string or null, e.g. "Beginner", "Intermediate", "Advanced">,
  "available_time": <integer in minutes per day or null>,
  "equipment": <string or null, e.g. "Dumbbells", "None / Bodyweight", "Full Gym">,
  "food_preference": <string or null, e.g. "Vegetarian", "Vegan", "Non-Vegetarian", "Eggetarian">,
  "food_restrictions": <string or null, e.g. "Lactose intolerant", "Gluten-free", "Peanut allergy", "None">,
  "budget": <float in local currency, exactly as stated by the user — do not convert or normalize the value or units>
}}
"""


def build_profile_extraction_prompt(user_input: str) -> dict:
    """
    Build the system and user prompts for profile extraction.

    Args:
        user_input: Raw natural language text from the user.

    Returns:
        dict with 'system' and 'user' prompt strings.
    """
    return {
        "system": PROFILE_EXTRACTION_SYSTEM_PROMPT.strip(),
        "user": PROFILE_EXTRACTION_USER_PROMPT.format(user_input=user_input.strip()).strip(),
    }
