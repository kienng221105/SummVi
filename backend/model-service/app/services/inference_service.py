import time
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.schemas.inference import SummarizeResponse
from ml.models.embedding_model import EmbeddingModel
from ml.models.vit5_model import ViT5Model
from ml.pipelines.evaluation_pipeline import EvaluationPipeline
from ml.pipelines.rag_pipeline import RAGPipeline
from ml.utils.summarization_prompts import MAX_SUMMARY_INPUT_WORDS, limit_input_words


class InferenceService:
    def __init__(self, rag_pipeline: RAGPipeline, evaluation_pipeline: EvaluationPipeline) -> None:
        self.rag_pipeline = rag_pipeline
        self.evaluation_pipeline = evaluation_pipeline

    def summarize(
        self,
        text: str,
        summary_length: str = "medium",
        output_format: str = "paragraph",
    ) -> SummarizeResponse:
        if not text or not text.strip():
            return SummarizeResponse(
                summary="",
                metrics={"length_ratio": 0.0, "compression_ratio": 1.0},
                diagnostics={},
            )

        limited_input = limit_input_words(text, max_words=MAX_SUMMARY_INPUT_WORDS)
        start = time.perf_counter()
        rag_result = self.rag_pipeline.run_with_diagnostics(
            limited_input.text,
            summary_length=summary_length,
            output_format=output_format,
        )
        summary = rag_result["summary"]
        latency = time.perf_counter() - start

        metrics = self.evaluation_pipeline.run(limited_input.text, summary)
        metrics["summary_word_count"] = float(len(summary.split()))
        metrics["input_word_count"] = float(limited_input.processed_word_count)

        diagnostics: dict[str, Any] = dict(rag_result)
        diagnostics.pop("summary", None)
        diagnostics["latency"] = latency

        return SummarizeResponse(summary=summary, metrics=metrics, diagnostics=diagnostics)


@lru_cache(maxsize=1)
def get_inference_service() -> InferenceService:
    rag_pipeline = RAGPipeline(
        model=ViT5Model(
            model_name=settings.vit5_model_name,
            cache_dir=str(settings.huggingface_dir),
        ),
        embedding_model=EmbeddingModel(
            model_name=settings.embedding_model_name,
            cache_dir=str(settings.huggingface_dir),
        ),
        persist_dir=str(settings.chroma_dir),
        collection_name="summvi_rag_chunks",
        top_k=settings.rag_top_k,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return InferenceService(
        rag_pipeline=rag_pipeline,
        evaluation_pipeline=EvaluationPipeline(),
    )
