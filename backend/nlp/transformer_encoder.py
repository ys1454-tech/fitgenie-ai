from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME, device="cpu")


def encode_texts(texts: list[str]):
    return _load_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )