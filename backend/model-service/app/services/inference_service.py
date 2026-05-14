import re
import time
from functools import lru_cache
from typing import Any
from app.core.config import settings
from app.schemas.inference import SummarizeResponse
from ml.models.vit5_model import ViT5Model, GenerationConfig
from ml.utils.summarization_prompts import generation_policy_for_length, summarize_prompt
VIT5_LOCAL_PATH = "/app/models/vit5/"
MODEL_CFG = GenerationConfig(
    max_output_tokens=512,
    num_beams=6,
    repetition_penalty=1.5,
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

        input_tokens = self.model.count_tokens(text)
        if input_tokens < 4 or not re.search(r"[a-zA-ZÀ-ỹ]", text):
            return SummarizeResponse(
                summary=text,
                metrics={},
                diagnostics={
                    "warning": "Input too short or contains no letters, returning as-is",
                },
            )

        generation_policy = generation_policy_for_length(
            input_tokens=input_tokens,
            summary_length=summary_length,
            style=output_format,
        )
        prompt = summarize_prompt(
            text,
            style=output_format,
            summary_length=summary_length,
        )

        max_new_tokens = int(generation_policy["max_new_tokens"])
        min_new_tokens = int(generation_policy["min_new_tokens"])
        length_penalty = float(generation_policy["length_penalty"])

        start = time.perf_counter()
        result = self.model.summarize(
            prompt,
            max_new_tokens=max_new_tokens,
            min_new_tokens=min_new_tokens,
            length_penalty=length_penalty,
        )
        summary = result.output_text
        if output_format == "bullet":
            summary = self._format_as_bullets(summary)
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
            diagnostics={
                "latency": latency,
                "input_tokens": float(input_tokens),
                "max_new_tokens": float(max_new_tokens),
                "min_new_tokens": float(min_new_tokens),
                "length_penalty": length_penalty,
                "summary_length": summary_length,
                "output_format": output_format,
            },
        )

    def _format_as_bullets(self, text: str) -> str:
        sentences = [
            sentence.strip(" -\t\n")
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
            if sentence.strip(" -\t\n")
        ]
        if not sentences:
            return text
        return "\n".join(f"- {sentence}" for sentence in sentences)

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
