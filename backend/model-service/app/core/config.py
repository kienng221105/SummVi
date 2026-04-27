import os
from dataclasses import dataclass
from pathlib import Path


def get_root_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docker-compose.yml").exists() or (parent / "warehouse").exists():
            return parent
    return Path("/app")


ROOT_DIR = get_root_dir()


@dataclass(frozen=True)
class Settings:
    app_name: str = "SummVi Model Service"
    app_version: str = "1.0.0"
    lite_mode: bool = os.getenv("LITE_MODE", "false").lower() in {"1", "true", "yes", "on"}
    vit5_model_name: str = os.getenv("VIT5_MODEL_NAME", "VietAI/vit5-base-vietnews-summarization")
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(ROOT_DIR / "chroma_data"))
    chroma_http_host: str | None = os.getenv("CHROMA_HTTP_HOST") or None
    chroma_http_port: int = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
    chroma_http_ssl: bool = os.getenv("CHROMA_HTTP_SSL", "false").lower() in {"1", "true", "yes", "on"}
    chroma_tenant: str = os.getenv("CHROMA_TENANT", "default_tenant")
    chroma_database: str = os.getenv("CHROMA_DATABASE", "default_database")
    huggingface_cache_dir: str = os.getenv("HF_HOME", str(ROOT_DIR / "data" / "models" / "cache"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "160"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "32"))

    @property
    def chroma_dir(self) -> Path:
        path = Path(self.chroma_persist_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def huggingface_dir(self) -> Path:
        path = Path(self.huggingface_cache_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
