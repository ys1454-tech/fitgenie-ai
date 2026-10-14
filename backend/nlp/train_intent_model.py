import csv
from pathlib import Path

import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "training_data.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_FILE = MODEL_DIR / "intent_classifier.joblib"


def load_training_data():
    texts = []
    labels = []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            texts.append(row["text"])
            labels.append(row["intent"])

    return texts, labels


def train():
    texts, labels = load_training_data()

    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000
                ),
            ),
        ]
    )

    model.fit(texts, labels)

    MODEL_DIR.mkdir(exist_ok=True)

    joblib.dump(model, MODEL_FILE)

    print(f"Intent model saved to: {MODEL_FILE}")


if __name__ == "__main__":
    train()