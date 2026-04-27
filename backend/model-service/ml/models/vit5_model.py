import os
from pathlib import Path

# Avoid top-level heavy imports to prevent MemoryError on startup
# import torch
# from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from ml.utils.summarization_prompts import (
    build_summary_prompt,
    format_fallback_summary,
    generation_max_new_tokens,
    normalize_output_format,
    normalize_summary_length,
)
from ml.utils.text_utils import clean_text, lead_sentences_summary


class ViT5Model:
    def __init__(self, model_name: str | None = None, cache_dir: str | None = None) -> None:
        selected_model = model_name or os.getenv("VIT5_MODEL_NAME", "VietAI/vit5-base-vietnews-summarization")
        self.model_name = selected_model
        self.cache_dir = Path(cache_dir or os.getenv("HF_HOME", "./data/models/cache")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir))
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        self.device = "cpu"
        self.tokenizer = None
        self.model = None
        self.load_error: str | None = None

        # Check for LITE_MODE to save memory
        lite_mode = os.getenv("LITE_MODE", "false").lower() in {"1", "true", "yes", "on"}
        if lite_mode:
            self.load_error = "LITE_MODE enabled: skipping heavy model load"
            return

        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tokenizer = AutoTokenizer.from_pretrained(
                selected_model,
                use_fast=False,
                cache_dir=str(self.cache_dir),
                local_files_only=True,
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                selected_model,
                cache_dir=str(self.cache_dir),
                local_files_only=True,
            )
            self.model.to(self.device)
            self.model.eval()
        except Exception as exc:
            self.load_error = str(exc)

    def summarize(self, text: str) -> str:
        return self.summarize_with_options(text, summary_length="medium", output_format="paragraph")

    def summarize_with_options(
        self,
        text: str,
        summary_length: str = "medium",
        output_format: str = "paragraph",
    ) -> str:
        """
        Tạo tóm tắt văn bản với các tùy chọn về độ dài và format.

        Logic:
        - Nếu model chưa load hoặc không có GPU: dùng extractive fallback (lead sentences)
        - Nếu có model + GPU: dùng ViT5 để generate abstractive summary
        - Fallback đảm bảo hệ thống vẫn hoạt động khi thiếu GPU hoặc model lỗi

        Args:
            text: Văn bản cần tóm tắt
            summary_length: "short" | "medium" | "long"
            output_format: "paragraph" | "bullet"
        """
        processed_text = clean_text(text)
        if not processed_text:
            return ""

        normalized_length = normalize_summary_length(summary_length)
        normalized_format = normalize_output_format(output_format)

        # Fallback: Nếu không có model hoặc GPU, dùng extractive summarization
        if self.model is None or self.tokenizer is None or self.device != "cuda":
            fallback_summary = lead_sentences_summary(
                processed_text,
                max_sentences=5 if normalized_length == "long" else 3 if normalized_length == "short" else 4,
                ratio=0.22 if normalized_length == "short" else 0.35 if normalized_length == "medium" else 0.5,
            )
            return format_fallback_summary(fallback_summary, normalized_format)

        prompt = build_summary_prompt(
            processed_text,
            summary_length=normalized_length,
            output_format=normalized_format,
        )

        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        max_new_tokens = generation_max_new_tokens(normalized_length)

        with torch.no_grad():
            output_ids = self.model.generate(
                **encoded,
                max_new_tokens=max_new_tokens,
                min_new_tokens=24 if normalized_length == "short" else 48 if normalized_length == "medium" else 72,
                num_beams=2,
                length_penalty=1.0,
                early_stopping=True,
            )

        decoded = clean_text(self.tokenizer.decode(output_ids[0], skip_special_tokens=True))
        if decoded:
            return format_fallback_summary(decoded, normalized_format)
        fallback_summary = lead_sentences_summary(
            processed_text,
            max_sentences=5 if normalized_length == "long" else 3 if normalized_length == "short" else 4,
            ratio=0.22 if normalized_length == "short" else 0.35 if normalized_length == "medium" else 0.5,
        )
        return format_fallback_summary(fallback_summary, normalized_format)

    @property
    def generation_backend(self) -> str:
        if self.model is not None and self.tokenizer is not None and self.device == "cuda":
            return "vit5"
        return "lead_sentences_fallback"

    def diagnostics(self) -> dict:
        gpu_memory_mb = None
        cuda_available = False
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_memory_mb = round(torch.cuda.memory_allocated() / (1024 * 1024), 4)
        except Exception:
            pass

        return {
            "model_name": self.model_name,
            "model_device": self.device,
            "generation_backend": self.generation_backend,
            "used_model_fallback": self.generation_backend != "vit5",
            "model_load_error": self.load_error,
            "cuda_available": cuda_available,
            "gpu_memory_mb": gpu_memory_mb,
        }
