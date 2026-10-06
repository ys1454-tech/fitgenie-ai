import json


PROFILE_EXTRACTION_SYSTEM_PROMPT = """You are FitGenie AI's profile extraction assistant.

Extract the user's fitness and nutrition profile into strict JSON.

The application has already performed a lightweight NLP analysis of the user's message.
The NLP output is only auxiliary information. The original user message is authoritative.

Use the NLP output to help identify relevant terms, but do not blindly trust it.
Resolve the user's actual meaning from the original message.

Respond ONLY with valid JSON.
"""


PROFILE_EXTRACTION_USER_PROMPT = """Extract the user profile from the following description.

USER MESSAGE:
"{user_input}"

APPLICATION NLP ANALYSIS:
{nlp_analysis}

Return a JSON object matching this exact schema:

{{
  "age": <integer or null>,
  "gender": <string or null>,
  "height": <float in cm or null>,
  "weight": <float in kg or null>,
  "fitness_goal": <string or null>,
  "fitness_level": <string or null>,
  "available_time": <integer in minutes per day or null>,
  "equipment": <string or null>,
  "food_preference": <string or null>,
  "food_restrictions": <string or null>,
  "budget": <float or null>
}}
"""


def build_profile_extraction_prompt(
    user_input: str,
    nlp_analysis: dict | None = None,
) -> dict:

    return {
        "system": PROFILE_EXTRACTION_SYSTEM_PROMPT.strip(),

        "user": PROFILE_EXTRACTION_USER_PROMPT.format(
            user_input=user_input.strip(),
            nlp_analysis=json.dumps(
                nlp_analysis or {},
                indent=2
            ),
        ).strip(),
    }