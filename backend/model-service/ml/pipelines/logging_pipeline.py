import os
import platform
from datetime import datetime
from typing import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import InferenceLog
from app.core.timezone import get_now


class LoggingPipeline:
    """
    Pipeline ghi log metrics của mỗi lần inference vào database để tracking và analytics.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        """
        Args:
            session_factory: Factory function tạo database session
                            (dùng factory thay vì truyền session trực tiếp để tránh session leak)
        """
        self.session_factory = session_factory

    def run(
        self,
        input_length: int,
        summary_length: int,
        input_word_count: int,
        summary_word_count: int,
        length_ratio: float,
        compression_ratio: float,
        latency: float,
        diagnostics: dict | None = None,
    ) -> None:
        """
        Ghi log một lần inference vào database.

        Metrics được log:
        - Input/output metrics: độ dài, số từ, tỷ lệ nén
        - Performance metrics: latency tổng, latency từng stage (RAG, retrieval, generation)
        - Model info: tên model, device, backend, load errors
        - System info: CPU count, Python version, platform, GPU memory
        - RAG config: top_k, chunk_size, overlap

        Error handling: Silent fail - nếu log thất bại không làm crash inference flow
        """
        session = self.session_factory()
        diagnostics = diagnostics or {}
        try:
            log = InferenceLog(
                input_length=input_length,
                summary_length=summary_length,
                input_word_count=input_word_count,
                summary_word_count=summary_word_count,
                length_ratio=length_ratio,
                compression_ratio=compression_ratio,
                latency=latency,
                rag_latency=diagnostics.get("rag_latency"),
                retrieval_latency=diagnostics.get("retrieval_latency"),
                generation_latency=diagnostics.get("generation_latency"),
                chunk_count=diagnostics.get("chunk_count"),
                retrieved_chunk_count=diagnostics.get("retrieved_chunk_count"),
                context_char_length=diagnostics.get("context_char_length"),
                model_name=diagnostics.get("model_name"),
                embedding_model_name=diagnostics.get("embedding_model_name"),
                model_device=diagnostics.get("model_device"),
                generation_backend=diagnostics.get("generation_backend"),
                embedding_backend=diagnostics.get("embedding_backend"),
                used_model_fallback=diagnostics.get("used_model_fallback"),
                model_load_error=diagnostics.get("model_load_error"),
                embedding_load_error=diagnostics.get("embedding_load_error"),
                rag_top_k=diagnostics.get("rag_top_k"),
                chunk_size=diagnostics.get("chunk_size"),
                chunk_overlap=diagnostics.get("chunk_overlap"),
                process_id=os.getpid(),
                cpu_count=os.cpu_count(),
                python_version=platform.python_version(),
                platform_name=platform.platform(),
                cuda_available=diagnostics.get("cuda_available"),
                gpu_memory_mb=diagnostics.get("gpu_memory_mb"),
                created_at=get_now(),
            )
            session.add(log)
            session.commit()
        except SQLAlchemyError:
            session.rollback()
        finally:
            session.close()
