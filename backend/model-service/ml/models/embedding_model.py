import os
from pathlib import Path
from typing import List

# Avoid top-level heavy imports to prevent MemoryError on startup
# from sentence_transformers import SentenceTransformer

from ml.utils.text_utils import clean_text, hashed_vector


class EmbeddingModel:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = Path(cache_dir or os.getenv("HF_HOME", "./data/models/cache")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir))
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        self.model = None
        self.load_error: str | None = None

        # Check for LITE_MODE to save memory
        lite_mode = os.getenv("LITE_MODE", "false").lower() in {"1", "true", "yes", "on"}
        if lite_mode:
            self.load_error = "LITE_MODE enabled: skipping heavy model load"
            return

        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(
                model_name,
                cache_folder=str(self.cache_dir),
                local_files_only=True,
            )
        except Exception as exc:
            self.load_error = str(exc)

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Chuyển đổi văn bản thành vector embeddings.

        Logic:
        - Nếu có model: dùng SentenceTransformer để tạo semantic embeddings
        - Nếu không có model (LITE_MODE hoặc lỗi): dùng hashed fallback
        - Hashed fallback: tạo vector deterministic từ hash của words (không semantic nhưng đủ dùng)

        Returns:
            List of embedding vectors (mỗi vector có 384 dimensions)
        """
        if not texts:
            return []

        cleaned_texts = [clean_text(text) for text in texts]
        if self.model is not None:
            return self.model.encode(cleaned_texts, normalize_embeddings=True).tolist()

        # Fallback: hash-based pseudo-embeddings khi không có model
        return [hashed_vector(text.split(), dimensions=384) for text in cleaned_texts]

    @property
    def embedding_backend(self) -> str:
        return "sentence_transformers" if self.model is not None else "hashed_fallback"

    def diagnostics(self) -> dict:
        return {
            "embedding_model_name": self.model_name,
            "embedding_backend": self.embedding_backend,
            "embedding_load_error": self.load_error,
        }
