import re
import spacy
from spacy.lang.en.stop_words import STOP_WORDS

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )


def preprocess_text(text: str) -> dict:
    """
    Basic NLP preprocessing:
    - lowercase
    - tokenization
    - stop-word removal
    - punctuation removal
    - lemmatization
    """

    text = text.strip()

    # Normalize spaces
    normalized_text = re.sub(r"\s+", " ", text.lower())

    doc = nlp(normalized_text)

    tokens = []
    lemmas = []

    for token in doc:
        if not token.is_space and not token.is_punct:
            tokens.append(token.text)

            if token.text not in STOP_WORDS:
                lemmas.append(token.lemma_)

    return {
        "original_text": text,
        "normalized_text": normalized_text,
        "tokens": tokens,
        "keywords": lemmas,
    }