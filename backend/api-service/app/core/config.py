import os
from dataclasses import dataclass
from pathlib import Path


def get_root_dir():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docker-compose.yml").exists() or (parent / "warehouse").exists():
            return parent
    return current.parents[4]

ROOT_DIR = get_root_dir()


@dataclass(frozen=True)
class Settings:
    app_name: str = "SummVi Vietnamese Summarization API"
    app_version: str = "2.0.0"
    api_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = tuple(os.getenv("CORS_ORIGINS", "*").split(","))
    lite_mode: bool = os.getenv("LITE_MODE", "false").lower() in {"1", "true", "yes", "on"}
    secret_key: str = os.getenv("SECRET_KEY", "")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    default_admin_email: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@summvi.local")
    default_admin_password: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "summarization")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    model_service_url: str = os.getenv("MODEL_SERVICE_URL", "http://model-service:8001")
    model_service_timeout_seconds: float = float(os.getenv("MODEL_SERVICE_TIMEOUT_SECONDS", "120"))
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    data_raw_dir: str = os.getenv("DATA_RAW_DIR", str(ROOT_DIR / "data" / "raw"))
    data_processed_dir: str = os.getenv("DATA_PROCESSED_DIR", str(ROOT_DIR / "data" / "processed"))
    data_features_dir: str = os.getenv("DATA_FEATURES_DIR", str(ROOT_DIR / "data" / "features"))
    data_metadata_dir: str = os.getenv("DATA_METADATA_DIR", str(ROOT_DIR / "data" / "metadata"))
    warehouse_export_dir: str = os.getenv("WAREHOUSE_EXPORT_DIR", str(ROOT_DIR / "warehouse" / "exports"))

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

settings = Settings()
