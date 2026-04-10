import os
from dataclasses import dataclass
from pathlib import Path


def get_root_dir():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "ml").exists() or (parent / "apps").exists():
            return parent
    return current.parents[2] # Fallback for local dev

ROOT_DIR = get_root_dir()


@dataclass(frozen=True)
class Settings:
    app_name: str = "SummVi Vietnamese Summarization API"
    app_version: str = "2.0.0"
    api_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = ("*",)
    lite_mode: bool = os.getenv("LITE_MODE", "false").lower() in {"1", "true", "yes", "on"}
    secret_key: str = os.getenv("SECRET_KEY", "")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    default_admin_email: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@summvi.local")
    default_admin_password: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(ROOT_DIR / "chroma_data"))
    chroma_http_host: str | None = os.getenv("CHROMA_HTTP_HOST") or None
    chroma_http_port: int = int(os.getenv("CHROMA_HTTP_PORT", "8000"))
    chroma_http_ssl: bool = os.getenv("CHROMA_HTTP_SSL", "false").lower() in {"1", "true", "yes", "on"}
    chroma_tenant: str = os.getenv("CHROMA_TENANT", "default_tenant")
    chroma_database: str = os.getenv("CHROMA_DATABASE", "default_database")
    vit5_model_name: str = os.getenv("VIT5_MODEL_NAME", "VietAI/vit5-base-vietnews-summarization")
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    huggingface_cache_dir: str = os.getenv("HF_HOME", str(ROOT_DIR / "data" / "models" / "cache"))
    data_raw_dir: str = os.getenv("DATA_RAW_DIR", str(ROOT_DIR / "data" / "raw"))
    data_processed_dir: str = os.getenv("DATA_PROCESSED_DIR", str(ROOT_DIR / "data" / "processed"))
    data_features_dir: str = os.getenv("DATA_FEATURES_DIR", str(ROOT_DIR / "data" / "features"))
    data_metadata_dir: str = os.getenv("DATA_METADATA_DIR", str(ROOT_DIR / "data" / "metadata"))
    warehouse_export_dir: str = os.getenv("WAREHOUSE_EXPORT_DIR", str(ROOT_DIR / "warehouse" / "exports"))
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    chunk_size: int = int(os.getenv("RAG_CHUNK_SIZE", "160"))
    chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "32"))

    @property
    def sqlalchemy_database_uri(self) -> str:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url

        return self.postgres_database_uri

    @property
    def prefers_postgres(self) -> bool:
        return bool(os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST"))

    @property
    def postgres_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def chroma_dir(self) -> Path:
        path = Path(self.chroma_persist_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def uses_remote_chroma(self) -> bool:
        return self.chroma_http_host is not None

    @property
    def huggingface_dir(self) -> Path:
        path = Path(self.huggingface_cache_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
