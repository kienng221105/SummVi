import time
from functools import lru_cache
from typing import Any
from app.core.config import settings
from app.schemas.inference import SummarizeResponse
from ml.models.vit5_model import ViT5Model, GenerationConfig
VIT5_LOCAL_PATH = "/app/models/vit5/"
MODEL_CFG = GenerationConfig(
    max_output_tokens=512,
    length_penalty=1.0,
    early_stopping=False,
)
class InferenceService:
    def __init__(self, model: ViT5Model) -> None:
        self.model = model

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

        start = time.perf_counter()
        result = self.model.summarize(text)
        summary = result.output_text
        latency = time.perf_counter() - start

        metrics = {
            "summary_word_count": float(len(summary.split())),
            "input_word_count": float(len(text.split())),
            "length_ratio": len(summary.split()) / max(len(text.split()), 1),
            "compression_ratio": 1.0 - (len(summary) / max(len(text), 1)),
        }

        return SummarizeResponse(
            summary=summary,
            metrics=metrics,
            diagnostics={"latency": latency},
        )

@lru_cache(maxsize=1)
def get_inference_service() -> InferenceService:
    try:
        model = ViT5Model(model_path=VIT5_LOCAL_PATH, config=MODEL_CFG)
    except Exception:
        model = ViT5Model(
            model_name=settings.vit5_model_name,
            cache_dir=str(settings.huggingface_dir),
        )
    return InferenceService(model=model)
