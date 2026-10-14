import re
import spacy


try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )


def build_entity_ruler():
    """
    Add custom fitness-domain entities.
    """

    ruler = nlp.add_pipe(
        "entity_ruler",
        before="ner",
        config={"overwrite_ents": False}
    )

    patterns = [
        # Fitness goals
        {"label": "FITNESS_GOAL", "pattern": "weight loss"},
        {"label": "FITNESS_GOAL", "pattern": "lose weight"},
        {"label": "FITNESS_GOAL", "pattern": "lose fat"},
        {"label": "FITNESS_GOAL", "pattern": "fat loss"},
        {"label": "FITNESS_GOAL", "pattern": "muscle gain"},
        {"label": "FITNESS_GOAL", "pattern": "gain muscle"},
        {"label": "FITNESS_GOAL", "pattern": "build muscle"},
        {"label": "FITNESS_GOAL", "pattern": "bulking"},
        {"label": "FITNESS_GOAL", "pattern": "endurance"},
        {"label": "FITNESS_GOAL", "pattern": "general fitness"},

        # Diet
        {"label": "DIET", "pattern": "vegetarian"},
        {"label": "DIET", "pattern": "vegan"},
        {"label": "DIET", "pattern": "non vegetarian"},
        {"label": "DIET", "pattern": "non-vegetarian"},
        {"label": "DIET", "pattern": "eggetarian"},

        # Equipment
        {"label": "EQUIPMENT", "pattern": "dumbbells"},
        {"label": "EQUIPMENT", "pattern": "dumbbell"},
        {"label": "EQUIPMENT", "pattern": "barbell"},
        {"label": "EQUIPMENT", "pattern": "resistance bands"},
        {"label": "EQUIPMENT", "pattern": "treadmill"},
        {"label": "EQUIPMENT", "pattern": "bench"},
        {"label": "EQUIPMENT", "pattern": "no equipment"},
        {"label": "EQUIPMENT", "pattern": "bodyweight"},

        # Fitness level
        {"label": "FITNESS_LEVEL", "pattern": "beginner"},
        {"label": "FITNESS_LEVEL", "pattern": "intermediate"},
        {"label": "FITNESS_LEVEL", "pattern": "advanced"},
    ]

    ruler.add_patterns(patterns)


# Add domain rules once
build_entity_ruler()


def _extract_numeric_entities(text: str) -> dict:
    """
    Extract domain values that are better handled with patterns/regex.
    """

    entities = {}

    age_match = re.search(
        r"\b(\d{1,3})\s*(?:years?\s*old|year old|yo)\b",
        text,
        re.IGNORECASE,
    )

    if age_match:
        entities["AGE"] = age_match.group(0)

    weight_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?)\b",
        text,
        re.IGNORECASE,
    )

    if weight_match:
        entities["WEIGHT"] = weight_match.group(0)

    height_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(cm|centimeters?|m tall|meters?)\b",
        text,
        re.IGNORECASE,
    )

    if height_match:
        entities["HEIGHT"] = height_match.group(0)

    workout_time_match = re.search(
        r"\b(\d+)\s*(minutes?|mins?|hours?)\b",
        text,
        re.IGNORECASE,
    )

    if workout_time_match:
        entities["WORKOUT_TIME"] = workout_time_match.group(0)

    workout_days_match = re.search(
        r"\b(\d+)\s*days?\b",
        text,
        re.IGNORECASE,
    )

    if workout_days_match:
        entities["WORKOUT_DAYS"] = workout_days_match.group(0)

    budget_match = re.search(
        r"(₹\s?[\d,]+|[\d,]+\s*(?:rupees?|rs|inr))"
        r"(?:\s*(?:per|/)\s*(day|week|month))?",
        text,
        re.IGNORECASE,
    )

    if budget_match:
        entities["BUDGET"] = budget_match.group(0)

    return entities


def extract_entities(text: str) -> dict:
    """
    Extract fitness-specific entities using spaCy EntityRuler
    plus regex-based numeric extraction.
    """

    doc = nlp(text)

    entities = {}

    for ent in doc.ents:
        entities.setdefault(ent.label_, []).append(ent.text)

    numeric_entities = _extract_numeric_entities(text)

    for key, value in numeric_entities.items():
        entities[key] = [value]

    return entities