import platform
import warnings
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BOOLEAN, CHAR, Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


Base = declarative_base()


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID

            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return value
        if isinstance(value, UUID):
            return value if dialect.name == "postgresql" else str(value)
        parsed = UUID(str(value))
        return parsed if dialect.name == "postgresql" else str(parsed)

    def process_result_value(self, value: Any, _dialect):
        if value is None:
            return value
        if isinstance(value, UUID):
            return value
        return UUID(str(value))


def _create_engine():
    database_uri = settings.sqlalchemy_database_uri
    
    try:
        # PostgreSQL connections should always use pool_pre_ping for production stability
        return create_engine(database_uri, pool_pre_ping=True)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to connect to PostgreSQL at {database_uri}. "
            "Ensure the database is running and credentials are correct. "
            f"Error: {exc}"
        ) from exc


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


from app.core.timezone import get_now


class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id = Column(Integer, primary_key=True, index=True)
    input_length = Column(Integer, nullable=False)
    summary_length = Column(Integer, nullable=False)
    input_word_count = Column(Integer, nullable=True)
    summary_word_count = Column(Integer, nullable=True)
    length_ratio = Column(Float, nullable=True)
    compression_ratio = Column(Float, nullable=False)
    latency = Column(Float, nullable=False)
    rag_latency = Column(Float, nullable=True)
    retrieval_latency = Column(Float, nullable=True)
    generation_latency = Column(Float, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    retrieved_chunk_count = Column(Integer, nullable=True)
    context_char_length = Column(Integer, nullable=True)
    model_name = Column(String(255), nullable=True)
    embedding_model_name = Column(String(255), nullable=True)
    model_device = Column(String(32), nullable=True)
    generation_backend = Column(String(64), nullable=True)
    embedding_backend = Column(String(64), nullable=True)
    used_model_fallback = Column(BOOLEAN, nullable=True)
    model_load_error = Column(Text, nullable=True)
    embedding_load_error = Column(Text, nullable=True)
    rag_top_k = Column(Integer, nullable=True)
    chunk_size = Column(Integer, nullable=True)
    chunk_overlap = Column(Integer, nullable=True)
    process_id = Column(Integer, nullable=True)
    cpu_count = Column(Integer, nullable=True)
    python_version = Column(String(64), nullable=True)
    platform_name = Column(String(128), nullable=True)
    cuda_available = Column(BOOLEAN, nullable=True)
    gpu_memory_mb = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)


def init_db() -> None:
    try:
        from app.models import analytics, conversation, document, message, rating, system_log, user, user_activity

        Base.metadata.create_all(bind=engine)
        _ensure_system_log_schema()
        _ensure_inference_log_schema()
        _ensure_user_schema()
        _seed_default_admin()
    except SQLAlchemyError as exc:
        warnings.warn(
            f"Database initialization skipped because the database is unavailable: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )


def get_db_session() -> Session:
    return SessionLocal()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_default_admin() -> None:
    from app.models.user import AppUser
    from app.services.auth_service import get_password_hash

    session = SessionLocal()
    try:
        admin = session.query(AppUser).filter(AppUser.email == settings.default_admin_email).first()
        if admin is None:
            session.add(
                AppUser(
                    email=settings.default_admin_email,
                    password_hash=get_password_hash(settings.default_admin_password),
                    role="admin",
                    is_active=True,
                )
            )
            session.commit()
    except SQLAlchemyError:
        session.rollback()
    finally:
        session.close()


def _ensure_system_log_schema() -> None:
    expected_columns = {
        "request_id": "VARCHAR(64)",
        "route_name": "VARCHAR(255)",
        "log_level": "VARCHAR(16) DEFAULT 'INFO'",
        "client_ip": "VARCHAR(64)",
        "user_agent": "VARCHAR(512)",
        "error_type": "VARCHAR(255)",
        "details": "TEXT",
    }

    inspector = inspect(engine)
    if "system_logs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("system_logs")}
    statements = [
        f"ALTER TABLE system_logs ADD COLUMN {column_name} {column_type}"
        for column_name, column_type in expected_columns.items()
        if column_name not in existing_columns
    ]

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_inference_log_schema() -> None:
    expected_columns = {
        "input_word_count": "INTEGER",
        "summary_word_count": "INTEGER",
        "length_ratio": "DOUBLE PRECISION",
        "rag_latency": "DOUBLE PRECISION",
        "retrieval_latency": "DOUBLE PRECISION",
        "generation_latency": "DOUBLE PRECISION",
        "chunk_count": "INTEGER",
        "retrieved_chunk_count": "INTEGER",
        "context_char_length": "INTEGER",
        "model_name": "VARCHAR(255)",
        "embedding_model_name": "VARCHAR(255)",
        "model_device": "VARCHAR(32)",
        "generation_backend": "VARCHAR(64)",
        "embedding_backend": "VARCHAR(64)",
        "used_model_fallback": "BOOLEAN",
        "model_load_error": "TEXT",
        "embedding_load_error": "TEXT",
        "rag_top_k": "INTEGER",
        "chunk_size": "INTEGER",
        "chunk_overlap": "INTEGER",
        "process_id": "INTEGER",
        "cpu_count": "INTEGER",
        "python_version": "VARCHAR(64)",
        "platform_name": "VARCHAR(128)",
        "cuda_available": "BOOLEAN",
        "gpu_memory_mb": "DOUBLE PRECISION",
    }

    inspector = inspect(engine)
    if "inference_logs" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("inference_logs")}
    statements = [
        f"ALTER TABLE inference_logs ADD COLUMN {column_name} {column_type}"
        for column_name, column_type in expected_columns.items()
        if column_name not in existing_columns
    ]

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_user_schema() -> None:
    """Add google_id column and make password_hash nullable if needed."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []

    if "google_id" not in existing_columns:
        statements.append("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE")

    # Make password_hash nullable (for Google-only users)
    # PostgreSQL syntax: ALTER COLUMN ... DROP NOT NULL
    try:
        statements.append("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    except Exception:
        pass

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except Exception:
                pass  # Column might already be nullable or already exist
