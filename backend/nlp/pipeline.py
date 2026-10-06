from .preprocessor import preprocess_text
from .entity_extractor import extract_entities
from .intent_classifier import classify_intent


def analyze_text(text: str) -> dict:
    """
    Complete NLP pipeline for FitGenie.
    """

    preprocessing = preprocess_text(text)
    entities = extract_entities(text)
    intent = classify_intent(text)

    return {
        "intent": intent["intent"],
        "intent_confidence": intent["confidence"],
        "tokens": preprocessing["tokens"],
        "keywords": preprocessing["keywords"],
        "entities": entities,
    }