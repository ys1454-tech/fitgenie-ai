import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api.routes.plans import (
    PlanModifyRequest,
    PlanSubstituteRequest,
    _invoke_validated_modification,
    _invoke_validated_plan,
    modify_plan,
    substitute_plan_food,
)
from prompts.plan_modification import build_plan_modification_prompt
from services.nutrition import NutritionValidationError, apply_food_substitution
from services.response_parser import (
    LLMResponseError,
    parse_llm_json,
    validate_plan_modification_response,
    validate_plan_response,
)


def meal_values(calories, protein, carbs, fat):
    return {
        "calories_kcal": calories,
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
    }


def sample_plan():
    values = {
        "breakfast": meal_values(400, 20, 50, 10),
        "lunch": meal_values(600, 40, 70, 20),
        "dinner": meal_values(500, 30, 50, 15),
        "snack": meal_values(150, 5, 20, 4),
    }
    day = {
        "workout": {
            "duration_minutes": 25,
            "exercises": [{"name": "Dumbbell row", "instructions": "Use dumbbells."}],
        },
        "nutrition": {
            "breakfast": "Oats with berries",
            "lunch": "Tofu bowl with rice",
            "dinner": "Lentil curry",
            "snack": "Apple",
            "meal_nutrition": values,
            "daily_nutrition_totals": {"calories_kcal": -1},
        },
    }
    return {
        "plan_title": "Test plan",
        "days": [
            {"day_number": day_number, "day_name": f"Day {day_number}", **json.loads(json.dumps(day))}
            for day_number in range(1, 8)
        ],
    }


def sample_profile():
    return {
        "available_time": 30,
        "equipment": "Dumbbells",
        "food_preference": "Vegetarian",
        "food_restrictions": "peanuts",
    }


def session_record():
    return SimpleNamespace(
        id="session-1",
        age=30,
        gender="Other",
        height=170,
        weight=70,
        fitness_goal="General fitness",
        fitness_level="Beginner",
        available_time=30,
        equipment="Dumbbells",
        food_preference="Vegetarian",
        food_restrictions="peanuts",
        budget=100,
    )


class NutritionTotalsTests(unittest.TestCase):
    def test_modification_prompt_requests_valid_compact_patch(self):
        prompt = build_plan_modification_prompt(
            "replace lunch with biryani", sample_plan(), sample_profile()
        )["user"]
        example = prompt.split("Return a JSON object with this exact structure. Include only affected days and changed fields:", 1)[1]
        example = example.split("###", 1)[0].strip()
        self.assertIn('"day_updates"', example)
        self.assertNotIn("return the full updated 7-day plan", prompt.lower())
        self.assertNotIn(",\n        }", example)

    def test_partial_plan_modification_preserves_omitted_days(self):
        existing = sample_plan()
        patch_data = {
            "modification_summary": "Changed Monday breakfast.",
            "day_updates": [{
                "day_number": 1,
                "nutrition": {
                    "breakfast": "Tofu scramble with toast",
                    "meal_nutrition": {"breakfast": meal_values(350, 30, 30, 10)},
                },
            }],
        }
        updated = validate_plan_modification_response(patch_data, existing, sample_profile())
        self.assertEqual(len(updated["days"]), 7)
        self.assertEqual(updated["days"][0]["nutrition"]["breakfast"], "Tofu scramble with toast")
        self.assertEqual(updated["days"][0]["nutrition"]["daily_nutrition_totals"]["calories_kcal"], 1600.0)
        self.assertEqual(updated["days"][6]["nutrition"]["lunch"], existing["days"][6]["nutrition"]["lunch"])

    def test_replace_lunch_with_biryani_updates_all_seven_days(self):
        biryani_estimate = meal_values(650, 22, 90, 18)
        patch_data = {
            "modification_summary": "Replaced lunch with vegetable biryani and raita for all seven days.",
            "day_updates": [
                {
                    "day_number": day_number,
                    "nutrition": {
                        "lunch": "Vegetable biryani with raita",
                        "meal_nutrition": {"lunch": biryani_estimate.copy()},
                    },
                }
                for day_number in range(1, 8)
            ],
        }

        updated = validate_plan_modification_response(patch_data, sample_plan(), sample_profile())
        self.assertEqual(len(updated["days"]), 7)
        for day in updated["days"]:
            self.assertEqual(day["nutrition"]["lunch"], "Vegetable biryani with raita")
            self.assertEqual(
                day["nutrition"]["daily_nutrition_totals"],
                {"calories_kcal": 1700.0, "protein_g": 77.0, "carbs_g": 210.0, "fat_g": 47.0},
            )

    def test_changed_meal_requires_replacement_nutrition(self):
        with self.assertRaises(LLMResponseError):
            validate_plan_modification_response(
                {"day_updates": [{"day_number": 1, "nutrition": {"lunch": "Vegetable biryani"}}]},
                sample_plan(),
                sample_profile(),
            )

    def test_incomplete_plan_is_retried_with_validation_feedback(self):
        incomplete = sample_plan()
        del incomplete["days"][6]["nutrition"]
        with patch(
            "api.routes.plans.gemini_service.invoke",
            side_effect=[json.dumps(incomplete), json.dumps(sample_plan())],
        ) as invoke:
            plan = _invoke_validated_plan(
                {"user": "Generate a complete plan", "system": "Return JSON"},
                sample_profile(),
            )

        self.assertEqual(len(plan["days"]), 7)
        self.assertEqual(invoke.call_count, 2)
        self.assertIn("missing 'nutrition' section", invoke.call_args.kwargs["user_prompt"])
        self.assertEqual(invoke.call_args.kwargs["max_tokens"], 8192)

    def test_parser_repairs_missing_delimiter(self):
        parsed = parse_llm_json(
            '{"plan_title":"Updated plan","days":[{"day_number":1 "day_name":"Monday"}]}'
        )
        self.assertEqual(parsed["days"][0]["day_name"], "Monday")

    def test_repaired_partial_plan_is_rejected(self):
        with self.assertRaises(LLMResponseError):
            validate_plan_response({"days": sample_plan()["days"][:6]}, sample_profile())

    def test_plan_modification_recalculates_totals_from_meals(self):
        plan = sample_plan()
        day_one = plan["days"][0]["nutrition"]
        day_one["breakfast"] = "Tofu scramble with toast"
        day_one["meal_nutrition"]["breakfast"] = meal_values(350, 30, 30, 10)

        validated = validate_plan_response(plan, sample_profile())
        self.assertEqual(
            validated["days"][0]["nutrition"]["daily_nutrition_totals"],
            {"calories_kcal": 1600.0, "protein_g": 105.0, "carbs_g": 170.0, "fat_g": 49.0},
        )
        self.assertEqual(
            validated["days"][1]["nutrition"]["daily_nutrition_totals"]["calories_kcal"],
            1650.0,
        )

    def test_substitution_updates_totals_and_keeps_profile_constraints(self):
        updated = apply_food_substitution(
            sample_plan(),
            1,
            "lunch",
            {
                "replacement_name": "Lentil rice bowl",
                "meal_description": "Lentil rice bowl with vegetables",
                "nutrition": meal_values(350, 25, 40, 10),
            },
            sample_profile(),
        )
        day_one = updated["days"][0]["nutrition"]
        self.assertEqual(day_one["lunch"], "Lentil rice bowl with vegetables")
        self.assertEqual(
            day_one["daily_nutrition_totals"],
            {"calories_kcal": 1400.0, "protein_g": 80.0, "carbs_g": 160.0, "fat_g": 39.0},
        )
        self.assertEqual(
            updated["days"][1]["nutrition"]["daily_nutrition_totals"]["calories_kcal"],
            1650.0,
        )

    def test_rejected_substitution_does_not_mutate_original_plan(self):
        plan = sample_plan()
        with self.assertRaises(NutritionValidationError):
            apply_food_substitution(
                plan,
                1,
                "lunch",
                {"meal_description": "Peanut tofu bowl", "nutrition": meal_values(350, 25, 40, 10)},
                sample_profile(),
            )
        self.assertEqual(plan["days"][0]["nutrition"]["lunch"], "Tofu bowl with rice")

        accepted = apply_food_substitution(
            plan,
            1,
            "lunch",
            {
                "meal_description": "Peanut-free tofu bowl",
                "nutrition": meal_values(350, 25, 40, 10),
            },
            sample_profile(),
        )
        self.assertEqual(accepted["days"][0]["nutrition"]["lunch"], "Peanut-free tofu bowl")

    def test_plan_modification_endpoint_saves_recalculated_plan(self):
        original = sample_plan()
        changed = {
            "modification_summary": "Changed Monday breakfast.",
            "day_updates": [{
                "day_number": 1,
                "nutrition": {
                    "breakfast": "Tofu scramble with toast",
                    "meal_nutrition": {"breakfast": meal_values(350, 30, 30, 10)},
                },
            }],
        }
        stored_plan = SimpleNamespace(id="plan-1", session_id="session-1", plan_content=json.dumps(original))
        saved_plan = SimpleNamespace(id="plan-2")

        with (
            patch("api.routes.plans.get_plan_by_id", return_value=stored_plan),
            patch("api.routes.plans.get_user_session", return_value=session_record()),
            patch("api.routes.plans.gemini_service.invoke", return_value=json.dumps(changed)),
            patch("api.routes.plans.save_plan", return_value=saved_plan) as save_mock,
        ):
            response = modify_plan("plan-1", PlanModifyRequest(user_request="Change breakfast"), object())

        saved_data = save_mock.call_args.args[2]
        self.assertEqual(response.plan_id, "plan-2")
        self.assertEqual(saved_data["days"][0]["nutrition"]["daily_nutrition_totals"]["calories_kcal"], 1600.0)
        self.assertEqual(saved_data["days"][1]["nutrition"]["daily_nutrition_totals"]["calories_kcal"], 1650.0)

    def test_substitution_endpoint_saves_recalculated_plan(self):
        stored_plan = SimpleNamespace(
            id="plan-1", session_id="session-1", plan_content=json.dumps(sample_plan())
        )
        saved_plan = SimpleNamespace(id="plan-2")
        replacement = {
            "replacement_name": "Lentil rice bowl",
            "meal_description": "Lentil rice bowl with vegetables",
            "nutrition": meal_values(350, 25, 40, 10),
        }

        with (
            patch("api.routes.plans.get_plan_by_id", return_value=stored_plan),
            patch("api.routes.plans.get_user_session", return_value=session_record()),
            patch("api.routes.plans.gemini_service.invoke", return_value=json.dumps(replacement)),
            patch("api.routes.plans.save_plan", return_value=saved_plan) as save_mock,
        ):
            response = substitute_plan_food(
                "plan-1",
                PlanSubstituteRequest(day_number=1, meal_slot="lunch", item_name="tofu"),
                object(),
            )

        saved_data = save_mock.call_args.args[2]
        self.assertEqual(response.plan_id, "plan-2")
        self.assertEqual(saved_data["days"][0]["nutrition"]["daily_nutrition_totals"]["calories_kcal"], 1400.0)
        self.assertIn("daily nutrition totals were recalculated", saved_data["modification_summary"])

    def test_inconsistent_calories_and_macros_are_rejected(self):
        plan = sample_plan()
        plan["days"][0]["nutrition"]["meal_nutrition"]["breakfast"] = meal_values(900, 5, 10, 2)
        with self.assertRaises(LLMResponseError):
            validate_plan_response(plan, sample_profile())

    def test_modified_plan_cannot_exceed_time_or_include_restricted_food(self):
        plan = sample_plan()
        plan["days"][0]["workout"]["duration_minutes"] = 31
        with self.assertRaises(LLMResponseError):
            validate_plan_response(plan, sample_profile())

        plan = sample_plan()
        plan["days"][0]["workout"]["duration_minutes"] = "30 minutes"
        with self.assertRaises(LLMResponseError):
            validate_plan_response(plan, sample_profile())

        plan = sample_plan()
        plan["days"][0]["workout"]["exercises"] = [
            {"name": "Barbell deadlift", "instructions": "Use a barbell."}
        ]
        with self.assertRaises(LLMResponseError):
            validate_plan_response(plan, sample_profile())

        plan = sample_plan()
        plan["days"][0]["nutrition"]["lunch"] = "Peanut tofu bowl"
        with self.assertRaises(LLMResponseError):
            validate_plan_response(plan, sample_profile())


if __name__ == "__main__":
    unittest.main()