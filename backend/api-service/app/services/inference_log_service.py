import os
import platform

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import InferenceLog
from app.core.timezone import get_now


DIAGNOSTIC_FIELDS = (
    "rag_latency",
    "retrieval_latency",
    "generation_latency",
    "chunk_count",
    "retrieved_chunk_count",
    "context_char_length",
    "model_name",
    "embedding_model_name",
    "model_device",
    "generation_backend",
    "embedding_backend",
    "used_model_fallback",
    "model_load_error",
    "embedding_load_error",
    "rag_top_k",
    "chunk_size",
    "chunk_overlap",
    "cuda_available",
    "gpu_memory_mb",
)


def create_inference_log(
    db: Session,
    *,
    input_length: int,
    summary_length: int,
    input_word_count: int,
    summary_word_count: int,
    length_ratio: float,
    compression_ratio: float,
    latency: float,
    diagnostics: dict | None = None,
) -> None:
    diagnostics = diagnostics or {}
    values = {field: diagnostics.get(field) for field in DIAGNOSTIC_FIELDS}

    record = InferenceLog(
        input_length=input_length,
        summary_length=summary_length,
        input_word_count=input_word_count,
        summary_word_count=summary_word_count,
        length_ratio=length_ratio,
        compression_ratio=compression_ratio,
        latency=latency,
        process_id=os.getpid(),
        cpu_count=os.cpu_count(),
        python_version=platform.python_version(),
        platform_name=platform.platform(),
        created_at=get_now(),
        **values,
    )

    try:
        db.add(record)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
