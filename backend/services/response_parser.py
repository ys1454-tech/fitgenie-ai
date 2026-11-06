"""
response_parser.py — Lightweight JSON parsing and validation for LLM responses.

Responsibilities:
  - Extract valid JSON from LLM output (stripping markdown fences or commentary).
  - Detect malformed/non-JSON responses.
  - Basic structural validation for each FitGenie AI task.
  - Return clear errors without crashing the FastAPI server.
"""

import copy
import json
import re

from json_repair import repair_json

from services.nutrition import (
    NutritionValidationError,
    recalculate_plan_nutrition,
    validate_meal_nutrition,
)


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
        try:
            repaired = json.loads(repair_json(candidate))
            if isinstance(repaired, (dict, list)):
                return repaired
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

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


def validate_plan_response(data: dict, profile: dict | None = None) -> dict:
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
    if len(days) != 7:
        raise LLMResponseError(
            f"Malformed plan response: expected 7 days, received {len(days)}."
        )

    # Check that each day has basic workout and nutrition structure
    for idx, day in enumerate(days):
        if not isinstance(day, dict):
            raise LLMResponseError(f"Malformed day entry at index {idx}: expected object, got {type(day).__name__}.")
        if "workout" not in day:
            raise LLMResponseError(f"Malformed day {day.get('day_number', idx + 1)}: missing 'workout' section.")
        if "nutrition" not in day:
            raise LLMResponseError(f"Malformed day {day.get('day_number', idx + 1)}: missing 'nutrition' section.")

    day_numbers = [day.get("day_number") for day in days]
    if any(isinstance(number, bool) or not isinstance(number, int) for number in day_numbers):
        raise LLMResponseError("Malformed plan response: each day must have an integer 'day_number'.")
    if set(day_numbers) != set(range(1, 8)):
        raise LLMResponseError("Malformed plan response: 'day_number' values must be 1 through 7, without duplicates.")

    try:
        recalculate_plan_nutrition(data, profile)
    except NutritionValidationError as exc:
        raise LLMResponseError(str(exc)) from exc

    return data


def validate_plan_modification_response(data: dict, existing_plan: dict, profile: dict) -> dict:
    """Merge a compact day-update response into the saved plan, then validate the whole plan."""
    if not isinstance(data, dict):
        raise LLMResponseError("Expected a JSON object for plan modification.")
    day_updates = data.get("day_updates")
    if not isinstance(day_updates, list) or not day_updates:
        raise LLMResponseError("Malformed plan modification: missing non-empty 'day_updates' list.")

    merged = copy.deepcopy(existing_plan)
    existing_days = merged.get("days")
    if not isinstance(existing_days, list):
        raise LLMResponseError("Existing plan is missing its 'days' list.")
    days_by_number = {day.get("day_number"): day for day in existing_days if isinstance(day, dict)}
    seen_days = set()

    for update in day_updates:
        if not isinstance(update, dict):
            raise LLMResponseError("Each day update must be a JSON object.")
        day_number = update.get("day_number")
        if isinstance(day_number, bool) or not isinstance(day_number, int):
            raise LLMResponseError("Each day update must include an integer 'day_number'.")
        if day_number in seen_days:
            raise LLMResponseError(f"Duplicate update for day {day_number}.")
        seen_days.add(day_number)
        day = days_by_number.get(day_number)
        if day is None:
            raise LLMResponseError(f"Day update references unknown day {day_number}.")

        allowed_day_fields = {"day_number", "day_name", "workout", "nutrition", "daily_notes"}
        unexpected = set(update) - allowed_day_fields
        if unexpected:
            raise LLMResponseError(f"Day {day_number} update contains unsupported fields: {sorted(unexpected)}.")
        if len(update) == 1:
            raise LLMResponseError(f"Day {day_number} update contains no changes.")

        for field in ("day_name", "daily_notes"):
            if field in update:
                day[field] = update[field]

        if "workout" in update:
            if not isinstance(update["workout"], dict):
                raise LLMResponseError(f"Day {day_number} workout update must be an object.")
            workout = day.get("workout")
            if not isinstance(workout, dict):
                workout = {}
            workout.update(update["workout"])
            day["workout"] = workout

        if "nutrition" in update:
            nutrition_update = update["nutrition"]
            if not isinstance(nutrition_update, dict):
                raise LLMResponseError(f"Day {day_number} nutrition update must be an object.")
            nutrition = day.get("nutrition")
            if not isinstance(nutrition, dict):
                nutrition = {}

            meal_nutrition_update = nutrition_update.get("meal_nutrition", {})
            if not isinstance(meal_nutrition_update, dict):
                raise LLMResponseError(f"Day {day_number} meal_nutrition update must be an object.")
            changed_meals = [
                slot for slot in ("breakfast", "lunch", "dinner", "snack")
                if slot in nutrition_update and nutrition_update[slot] != nutrition.get(slot)
            ]
            missing_estimates = [slot for slot in changed_meals if slot not in meal_nutrition_update]
            if missing_estimates:
                raise LLMResponseError(
                    f"Day {day_number} changed meal(s) {', '.join(missing_estimates)} without updated nutrition estimates."
                )

            for key, value in nutrition_update.items():
                if key == "meal_nutrition":
                    meal_nutrition = nutrition.get("meal_nutrition")
                    if not isinstance(meal_nutrition, dict):
                        meal_nutrition = {}
                    meal_nutrition.update(meal_nutrition_update)
                    nutrition["meal_nutrition"] = meal_nutrition
                else:
                    nutrition[key] = value
            day["nutrition"] = nutrition

    if "modification_summary" in data:
        merged["modification_summary"] = data["modification_summary"]
    if "plan_title" in data:
        merged["plan_title"] = data["plan_title"]

    return validate_plan_response(merged, profile)


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

    if not data.get("meal_description"):
        raise LLMResponseError("Malformed substitution response: missing 'meal_description'.")

    try:
        data["nutrition"] = validate_meal_nutrition(data.get("nutrition"), "substitution nutrition")
    except NutritionValidationError as exc:
        raise LLMResponseError(str(exc)) from exc

    return data
