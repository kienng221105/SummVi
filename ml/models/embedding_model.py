import os
from pathlib import Path
from typing import List

from sentence_transformers import SentenceTransformer

from ml.utils.text_utils import clean_text, hashed_vector


class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = Path(cache_dir or os.getenv("HF_HOME", "./data/models/cache")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir))

        self.model = None
        self.load_error: str | None = None

        try:
            self.model = SentenceTransformer(model_name, cache_folder=str(self.cache_dir))
        except Exception as exc:
            self.load_error = str(exc)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        cleaned_texts = [clean_text(text) for text in texts]
        if self.model is not None:
            return self.model.encode(cleaned_texts, normalize_embeddings=True).tolist()

        return [hashed_vector(text.split()) for text in cleaned_texts]

    @property
    def embedding_backend(self) -> str:
        return "sentence_transformers" if self.model is not None else "hashed_fallback"

    def diagnostics(self) -> dict:
        return {
            "embedding_model_name": self.model_name,
            "embedding_backend": self.embedding_backend,
            "embedding_load_error": self.load_error,
        }
