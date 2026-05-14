import re
from dataclasses import dataclass, field
from enum import Enum
import torch
from transformers import AutoModelForSeq2SeqLM, T5Tokenizer
class TruncationBehavior(str, Enum):
    WARN = "warn"
    RAISE = "raise"
    
class ViT5TruncationError(ValueError):
    pass
@dataclass
class GenerationConfig:
    max_input_tokens: int = 2048
    max_output_tokens: int = 256
    num_beams: int = 4
    length_penalty: float = 1.0
    no_repeat_ngram_size: int = 3
    repetition_penalty: float = 1.3
    early_stopping: bool = True
    truncation_behavior: TruncationBehavior = TruncationBehavior.WARN

@dataclass
class ViT5Output:
    output_text: str
    input_token_count: int
    output_token_count: int
    was_truncated: bool
    warnings: list[str] = field(default_factory=list)
    
class ViT5Model:
    MODEL_NAME = "VietAI/vit5-base-vietnews-summarization"
    def __init__(
        self,
        model_path: str | None = None,
        model_name: str | None = None,
        cache_dir: str | None = None,
        device: str | None = None,
        config: GenerationConfig | None = None,
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.config = config or GenerationConfig()
        load_path = model_path or model_name or self.MODEL_NAME
        self.tokenizer = self._load_tokenizer(load_path, cache_dir=cache_dir)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(load_path, cache_dir=cache_dir)
        self.model.eval()
        self.model.to(self.device)

    def summarize(
        self,
        text: str,
        max_new_tokens: int | None = None,
        min_new_tokens: int | None = None,
        length_penalty: float | None = None,
    ) -> ViT5Output:
        text = self._fix_broken_words(text)
        return self._generate(
            text,
            max_new_tokens=max_new_tokens,
            min_new_tokens=min_new_tokens,
            length_penalty=length_penalty,
        )

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def _generate(
        self,
        prompt: str,
        max_new_tokens: int | None = None,
        min_new_tokens: int | None = None,
        length_penalty: float | None = None,
    ) -> ViT5Output:
        warnings = []
        encoded = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=False,
            padding=False,
        )
        input_token_count = encoded["input_ids"].shape[1]
        was_truncated = False
        effective_max = max_new_tokens or self.config.max_output_tokens
        effective_min = min_new_tokens
        effective_length_penalty = length_penalty or self.config.length_penalty
        if input_token_count > self.config.max_input_tokens:
            if self.config.truncation_behavior == TruncationBehavior.RAISE:
                raise ViT5TruncationError(
                    f"Input {input_token_count} tokens > max "
                    f"{self.config.max_input_tokens}. Use map-reduce pipeline "
                    "for long inputs."
                )
            was_truncated = True
            warnings.append(f"Input truncated: {input_token_count} tokens")
            encoded = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_input_tokens,
                padding=False,
            )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        generation_kwargs = {
            "max_new_tokens": effective_max,
            "num_beams": self.config.num_beams,
            "length_penalty": effective_length_penalty,
            "no_repeat_ngram_size": self.config.no_repeat_ngram_size,
            "repetition_penalty": self.config.repetition_penalty,
            "early_stopping": self.config.early_stopping,
        }
        if effective_min is not None:
            generation_kwargs["min_new_tokens"] = effective_min
        with torch.no_grad():
            output_ids = self.model.generate(
                **encoded,
                **generation_kwargs,
            )
        output_token_count = output_ids.shape[1]
        output_text = str(self.tokenizer.decode(output_ids[0], skip_special_tokens=True))
        output_text = self._post_process(output_text)
        return ViT5Output(
            output_text=output_text,
            input_token_count=int(input_token_count),
            output_token_count=int(output_token_count),
            was_truncated=was_truncated,
            warnings=warnings,
        )

    def _post_process(self, text: str) -> str:
        text = text.strip()
        text = self._remove_repeated_sentences(text)
        text = self._trim_incomplete_sentence(text)
        text = self._normalize_vietnamese_text(text)
        return text

    def _normalize_vietnamese_text(self, text: str) -> str:
        # Sửa lỗi gõ và ghép từ phổ biến của ViT5
        replacements = {
            r"\b(C|c)vì\b": r"\1vì",
            r"nilông": "ni-lông",
            r"k ho": "kho",
            r"\s+([,.!?])": r"\1",
            r"([,.!?])([A-Za-zÀ-Ỹà-ỹ])": r"\1 \2",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        protected = {
            "TP.HCM": "TP_HCM",
            "v.v.": "v_v_",
            "V.V.": "V_V_",
            "PGS.TS": "PGS_TS",
            "ThS.": "ThS_",
            "TS.": "TS_",
            "GS.": "GS_",
            "tr.CN": "tr_CN",
        }
        for original, replacement in protected.items():
            text = text.replace(original, replacement)
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?;:])\s+|\n+", text)
            if sentence.strip()
        ]
        restored = []
        for sentence in sentences:
            for original, replacement in protected.items():
                sentence = sentence.replace(replacement, original)
            restored.append(sentence)
        return restored

    def _remove_repeated_sentences(self, text: str) -> str:
        sentences = self._split_sentences(text)
        seen = set()
        kept = []
        for sentence in sentences:
            key = re.sub(r"\W+", " ", sentence.lower()).strip()
            if key and key not in seen:
                seen.add(key)
                kept.append(sentence)
        return " ".join(kept)

    def _trim_incomplete_sentence(self, text: str) -> str:
        end_markers = (".", "!", "?", "…")
        if text.endswith(end_markers):
            return text
        sentences = self._split_sentences(text)
        if sentences and not sentences[-1].endswith(end_markers):
            sentences = sentences[:-1]
        return " ".join(sentences) if sentences else text

    def _fix_broken_words(self, text: str) -> str:
        pattern = re.compile(
            r"\b([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])"
            r"\s"
            r"([a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]{2,})",
        )
        prev = None
        while prev != text:
            prev = text
            text = pattern.sub(r"\1\2", text)
        return text

    def _load_tokenizer(self, model_path: str, cache_dir: str | None = None) -> T5Tokenizer:
        try:
            return T5Tokenizer.from_pretrained(model_path, legacy=True, cache_dir=cache_dir)
        except Exception:
            from huggingface_hub import hf_hub_download
            vocab = hf_hub_download(
                repo_id="VietAI/vit5-base",
                filename="spiece.model",
                cache_dir=cache_dir,
            )
            return T5Tokenizer(vocab_file=vocab, legacy=True)
