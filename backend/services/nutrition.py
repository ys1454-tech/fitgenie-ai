"""Deterministic nutrition-total calculation and plan constraint checks."""

import copy
import json
import re
from math import isfinite


MEAL_SLOTS = ("breakfast", "lunch", "dinner", "snack")
NUTRIENT_FIELDS = ("calories_kcal", "protein_g", "carbs_g", "fat_g")

_DIETARY_EXCLUSIONS = {
    "vegetarian": (
        "beef", "pork", "chicken", "turkey", "lamb", "meat", "fish", "seafood",
        "prawn", "shrimp", "bacon", "ham", "gelatin",
    ),
    "vegan": (
        "beef", "pork", "chicken", "turkey", "lamb", "meat", "fish", "seafood",
        "prawn", "shrimp", "bacon", "ham", "gelatin", "egg", "milk", "dairy",
        "cheese", "yogurt", "butter", "ghee", "honey", "cream",
    ),
}

_EQUIPMENT_TERMS = (
    "barbell", "dumbbell", "kettlebell", "resistance band", "bench", "cable machine",
    "pull-up bar", "pull up bar", "treadmill", "jump rope", "skipping rope",
    "medicine ball", "rowing machine",
)


class NutritionValidationError(ValueError):
    """Raised when plan nutrition data or user constraints are invalid."""


def _number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NutritionValidationError(f"{label} must be a non-negative number.")
    if not isfinite(value) or value < 0:
        raise NutritionValidationError(f"{label} must be a finite, non-negative number.")
    return float(value)


def validate_meal_nutrition(values: dict, label: str = "meal_nutrition") -> dict:
    if not isinstance(values, dict):
        raise NutritionValidationError(f"{label} must be an object.")
    normalized = {
        nutrient: _number(values.get(nutrient), f"{label}.{nutrient}")
        for nutrient in NUTRIENT_FIELDS
    }
    macro_calories = (
        4 * normalized["protein_g"]
        + 4 * normalized["carbs_g"]
        + 9 * normalized["fat_g"]
    )
    tolerance = max(50, normalized["calories_kcal"] * 0.25, macro_calories * 0.25)
    if abs(normalized["calories_kcal"] - macro_calories) > tolerance:
        raise NutritionValidationError(
            f"{label} calories are inconsistent with the protein, carbohydrate, and fat estimates."
        )
    return normalized


def _normalized_text(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _contains_food_or_equipment_term(text: str, term: str) -> bool:
    for match in re.finditer(rf"\b{re.escape(term)}\b", text):
        before = text[:match.start()].split()
        after = text[match.end():].split()
        if before and before[-1] in {"no", "without", "avoid"}:
            continue
        if len(before) >= 2 and before[-2:] in (["free", "from"], ["free", "of"]):
            continue
        if after and after[0] == "free":
            continue
        return True
    return False


def _restricted_ingredients(restrictions) -> list[str]:
    text = _normalized_text(restrictions)
    if text in {"", "none", "no", "n a", "na", "no restrictions", "none known"}:
        return []
    terms = re.split(r"[,;|]|and|or", text)
    ignored = {"allergy", "allergies", "allergic", "intolerance", "intolerant", "avoid", "avoidance", "to"}
    normalized_terms = []
    for term in terms:
        ingredient = " ".join(word for word in term.split() if word not in ignored)
        if not ingredient:
            continue
        normalized_terms.append(ingredient)
        words = ingredient.split()
        last_word = words[-1]
        if last_word.endswith("ies") and len(last_word) > 3:
            words[-1] = last_word[:-3] + "y"
            normalized_terms.append(" ".join(words))
        elif last_word.endswith("s") and not last_word.endswith(("ss", "us")):
            words[-1] = last_word[:-1]
            normalized_terms.append(" ".join(words))
    return normalized_terms


def validate_plan_constraints(plan: dict, profile: dict) -> None:
    allowed_time = profile.get("available_time")
    if isinstance(allowed_time, (int, float)) and not isinstance(allowed_time, bool):
        for day in plan.get("days", []):
            duration = (day.get("workout") or {}).get("duration_minutes")
            if isinstance(duration, bool) or not isinstance(duration, (int, float)):
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: workout duration must be numeric to check the user's time limit."
                )
            if duration > allowed_time:
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: workout duration exceeds the user's {allowed_time}-minute limit."
                )

    profile_text = _normalized_text(profile.get("food_preference"))
    food_terms = {
        "vegetarian": _DIETARY_EXCLUSIONS["vegetarian"],
        "vegan": _DIETARY_EXCLUSIONS["vegan"],
    }
    exclusions = food_terms["vegan"] if "vegan" in profile_text else (
        food_terms["vegetarian"] if "vegetarian" in profile_text else ()
    )
    restricted_terms = [term for term in _restricted_ingredients(profile.get("food_restrictions")) if term]

    available_equipment = _normalized_text(profile.get("equipment"))
    equipment_is_unset = available_equipment in {"", "none", "no equipment", "bodyweight", "body weight"}

    for day in plan.get("days", []):
        nutrition = day.get("nutrition") or {}
        meals_text = " ".join(str(nutrition.get(slot, "")) for slot in MEAL_SLOTS)
        normalized_meals = _normalized_text(meals_text)
        for ingredient in restricted_terms:
            if ingredient and _contains_food_or_equipment_term(normalized_meals, ingredient):
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: meal includes restricted ingredient '{ingredient}'."
                )
        for ingredient in exclusions:
            if _contains_food_or_equipment_term(normalized_meals, ingredient):
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: meal conflicts with the user's {profile_text} preference."
                )

        workout_text = _normalized_text(json.dumps(day.get("workout") or {}, ensure_ascii=False))
        for equipment in _EQUIPMENT_TERMS:
            normalized_equipment = _normalized_text(equipment)
            if _contains_food_or_equipment_term(workout_text, normalized_equipment) and (
                equipment_is_unset or equipment not in available_equipment
            ):
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: workout uses unavailable equipment '{equipment}'."
                )


def recalculate_plan_nutrition(plan: dict, profile: dict | None = None) -> dict:
    """Validate per-meal estimates and overwrite each day's derived totals."""
    days = plan.get("days")
    if not isinstance(days, list) or not days:
        raise NutritionValidationError("Plan must contain at least one day.")

    for day in days:
        nutrition = day.get("nutrition")
        if not isinstance(nutrition, dict):
            raise NutritionValidationError(f"Day {day.get('day_number')}: nutrition must be an object.")
        meal_values = nutrition.get("meal_nutrition")
        if not isinstance(meal_values, dict):
            raise NutritionValidationError(
                f"Day {day.get('day_number')}: missing per-meal nutrition estimates."
            )

        totals = dict.fromkeys(NUTRIENT_FIELDS, 0.0)
        for slot in MEAL_SLOTS:
            if slot not in meal_values:
                raise NutritionValidationError(
                    f"Day {day.get('day_number')}: missing {slot} nutrition estimates."
                )
            meal_values[slot] = validate_meal_nutrition(
                meal_values[slot], f"day {day.get('day_number')} {slot}"
            )
            for nutrient in NUTRIENT_FIELDS:
                totals[nutrient] += meal_values[slot][nutrient]

        nutrition["daily_nutrition_totals"] = {
            nutrient: round(value, 1) for nutrient, value in totals.items()
        }

    if profile is not None:
        validate_plan_constraints(plan, profile)
    return plan


def apply_food_substitution(
    plan: dict,
    day_number: int,
    meal_slot: str,
    substitution: dict,
    profile: dict,
) -> dict:
    """Apply one validated food replacement and recalculate all affected totals."""
    if meal_slot not in MEAL_SLOTS:
        raise NutritionValidationError(f"Unsupported meal slot '{meal_slot}'.")
    updated_plan = copy.deepcopy(plan)
    day = next((item for item in updated_plan.get("days", []) if item.get("day_number") == day_number), None)
    if day is None:
        raise NutritionValidationError(f"Day {day_number} was not found in the plan.")
    if not isinstance(substitution, dict) or not substitution.get("meal_description"):
        raise NutritionValidationError("Substitution must include a meal_description.")

    nutrition = day.get("nutrition") or {}
    meal_values = nutrition.get("meal_nutrition")
    if not isinstance(meal_values, dict):
        raise NutritionValidationError(f"Day {day_number}: missing per-meal nutrition estimates.")

    nutrition[meal_slot] = substitution["meal_description"]
    meal_values[meal_slot] = validate_meal_nutrition(
        substitution.get("nutrition"), f"substitution {meal_slot}"
    )
    day["nutrition"] = nutrition
    return recalculate_plan_nutrition(updated_plan, profile)