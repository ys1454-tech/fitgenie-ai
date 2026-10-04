"""
response_parser.py — Lightweight JSON parsing and validation for LLM responses.

Responsibilities:
  - Extract valid JSON from LLM output (stripping markdown fences or commentary).
  - Detect malformed/non-JSON responses.
  - Basic structural validation for each FitGenie AI task.
  - Return clear errors without crashing the FastAPI server.
"""

import json
import re


class LLMResponseError(Exception):
    """Raised when an LLM response cannot be parsed or fails basic validation."""

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.message = message
        self.raw_response = raw_response


def clean_llm_json_text(text: str) -> str:
    """
    Extract the JSON portion from an LLM response string.
    Handles responses wrapped in markdown fences (```json ... ```)
    or preceded/followed by conversational text.

    Args:
        text: Raw text string from the LLM.

    Returns:
        Cleaned substring containing only the JSON candidate.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # Pattern 1: Markdown code fences: ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    fence_match = re.search(fence_pattern, cleaned, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # Pattern 2: Find outermost JSON object {...} or array [...]
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1].strip()

    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return cleaned[first_bracket : last_bracket + 1].strip()

    return cleaned


def parse_llm_json(raw_text: str) -> dict | list:
    """
    Parse an LLM response string into a Python dict or list.

    Args:
        raw_text: Raw response string from Amazon Bedrock.

    Returns:
        Parsed JSON data as a dict or list.

    Raises:
        LLMResponseError if parsing fails.
    """
    if not raw_text or not raw_text.strip():
        raise LLMResponseError("LLM returned an empty response.", raw_response=raw_text)

    candidate = clean_llm_json_text(raw_text)

    try:
        data = json.loads(candidate)
        return data
    except json.JSONDecodeError as exc:
        snippet = raw_text[:200] + ("..." if len(raw_text) > 200 else "")
        raise LLMResponseError(
            f"Failed to parse LLM response as JSON: {exc.msg} at line {exc.lineno}, col {exc.colno}. Snippet: {snippet}",
            raw_response=raw_text,
        ) from exc


def validate_profile_extraction_response(data: dict) -> dict:
    """
    Validate that the parsed JSON conforms to the profile extraction schema.

    Returns:
        Cleaned dictionary with recognized profile keys.
    """
    if not isinstance(data, dict):
        raise LLMResponseError(f"Expected a JSON object for profile extraction, got {type(data).__name__}.")

    expected_keys = {
        "age",
        "gender",
        "height",
        "weight",
        "fitness_goal",
        "fitness_level",
        "available_time",
        "equipment",
        "food_preference",
        "food_restrictions",
        "budget",
    }

    # Ensure keys are present or defaulted to None
    result = {}
    for key in expected_keys:
        result[key] = data.get(key)

    return result


def validate_plan_response(data: dict) -> dict:
    """
    Validate that the parsed JSON conforms to the 7-day plan schema.

    Returns:
        The validated plan dictionary.
    """
    if not isinstance(data, dict):
        raise LLMResponseError(f"Expected a JSON object for plan, got {type(data).__name__}.")

    if "days" not in data or not isinstance(data["days"], list):
        raise LLMResponseError("Malformed plan response: missing 'days' list in JSON output.")

    days = data["days"]
    if len(days) == 0:
        raise LLMResponseError("Malformed plan response: 'days' list is empty.")

    # Check that each day has basic workout and nutrition structure
    for idx, day in enumerate(days):
        if not isinstance(day, dict):
            raise LLMResponseError(f"Malformed day entry at index {idx}: expected object, got {type(day).__name__}.")
        if "workout" not in day:
            raise LLMResponseError(f"Malformed day {day.get('day_number', idx + 1)}: missing 'workout' section.")
        if "nutrition" not in day:
            raise LLMResponseError(f"Malformed day {day.get('day_number', idx + 1)}: missing 'nutrition' section.")

    return data


def validate_substitution_response(data: dict) -> dict:
    """
    Validate that the parsed JSON conforms to the substitution schema.

    Returns:
        The validated substitution dictionary.
    """
    if not isinstance(data, dict):
        raise LLMResponseError(f"Expected a JSON object for substitution, got {type(data).__name__}.")

    if not data.get("replacement_name"):
        raise LLMResponseError("Malformed substitution response: missing 'replacement_name'.")

    return data
