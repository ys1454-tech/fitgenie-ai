from pathlib import Path

import joblib


MODEL_FILE = (
    Path(__file__).resolve().parent
    / "models"
    / "intent_classifier.joblib"
)


if not MODEL_FILE.exists():
    raise RuntimeError(
        "Intent model not found. Run: python -m nlp.train_intent_model"
    )


model = joblib.load(MODEL_FILE)


def classify_intent(text: str) -> dict:
    """
    Predict user intent and return confidence.
    """

    predicted_intent = model.predict([text])[0]

    probabilities = model.predict_proba([text])[0]
    confidence = float(max(probabilities))

    return {
        "intent": predicted_intent,
        "confidence": round(confidence, 4),
    }