from __future__ import annotations

import re

from dataclasses import dataclass

from ml.utils.text_utils import clean_text, split_sentences

MAX_SUMMARY_INPUT_WORDS = 5000

SUMMARY_LENGTH_INSTRUCTIONS = {
    "short": "Viết bản tóm tắt ngắn, chỉ giữ 3-5 ý quan trọng nhất, khoảng 80-120 từ.",
    "medium": "Viết bản tóm tắt vừa phải, giữ các ý chính và thông tin cốt lõi, khoảng 180-260 từ.",
    "long": "Viết bản tóm tắt dài, đầy đủ bối cảnh, luận điểm và chi tiết quan trọng, khoảng 320-500 từ.",
}

OUTPUT_FORMAT_INSTRUCTIONS = {
    "bullet": "Trình bày kết quả dưới dạng gạch đầu dòng. Mỗi dòng là một ý rõ ràng, không viết thành đoạn văn dài.",
    "keypoints": "Trình bày kết quả dưới dạng các ý chính tách dòng. Mỗi dòng là một ý rõ ràng, không viết thành đoạn văn dài.",
    "paragraph": "Trình bày kết quả thành một hoặc nhiều đoạn văn tự nhiên, không dùng gạch đầu dòng hay đánh số.",
}

GENERATION_MAX_NEW_TOKENS = {
    "short": 128,
    "medium": 192,
    "long": 280,
}


@dataclass(frozen=True)
class TruncationResult:
    text: str
    original_word_count: int
    processed_word_count: int
    truncated: bool


def limit_input_words(text: str, max_words: int = MAX_SUMMARY_INPUT_WORDS) -> TruncationResult:
    normalized = clean_text(text)
    words = normalized.split()
    original_word_count = len(words)

    if original_word_count <= max_words:
        return TruncationResult(
            text=normalized,
            original_word_count=original_word_count,
            processed_word_count=original_word_count,
            truncated=False,
        )

    limited_text = " ".join(words[:max_words]).strip()
    return TruncationResult(
        text=limited_text,
        original_word_count=original_word_count,
        processed_word_count=max_words,
        truncated=True,
    )


def normalize_summary_length(summary_length: str | None) -> str:
    value = (summary_length or "medium").strip().lower()
    return value if value in SUMMARY_LENGTH_INSTRUCTIONS else "medium"


def normalize_output_format(output_format: str | None) -> str:
    value = (output_format or "paragraph").strip().lower()
    return value if value in OUTPUT_FORMAT_INSTRUCTIONS else "paragraph"


def generation_max_new_tokens(summary_length: str | None) -> int:
    normalized_length = normalize_summary_length(summary_length)
    return GENERATION_MAX_NEW_TOKENS[normalized_length]


def build_summary_prompt(text: str, summary_length: str = "medium", output_format: str = "paragraph") -> str:
    normalized_length = normalize_summary_length(summary_length)
    normalized_format = normalize_output_format(output_format)
    length_instruction = SUMMARY_LENGTH_INSTRUCTIONS[normalized_length]
    format_instruction = OUTPUT_FORMAT_INSTRUCTIONS[normalized_format]

    return "\n".join(
        [
            "Bạn là hệ thống tóm tắt tiếng Việt chuyên nghiệp.",
            "Nhiệm vụ: tóm tắt văn bản nguồn theo đúng yêu cầu bên dưới.",
            f"Độ dài tóm tắt: {length_instruction}",
            f"Định dạng đầu ra: {format_instruction}",
            "Quy tắc:",
            "- Chỉ trả về kết quả tóm tắt cuối cùng.",
            "- Không giải thích quy trình, không thêm tiêu đề, không thêm lời mở đầu.",
            "- Giữ nguyên số liệu, tên riêng và mốc thời gian quan trọng.",
            "- Nếu văn bản có nhiều ý, ưu tiên ý chính trước, sau đó mới tới chi tiết hỗ trợ.",
            "Văn bản nguồn:",
            '"""',
            clean_text(text),
            '"""',
        ]
    )


def format_fallback_summary(summary: str, output_format: str = "paragraph") -> str:
    normalized_summary = clean_text(summary)
    normalized_format = normalize_output_format(output_format)

    if not normalized_summary:
        return ""

    if normalized_format in {"bullet", "keypoints"}:
        # Split into sentences and cleanup each one
        raw_sentences = split_sentences(normalized_summary) or [normalized_summary]
        formatted_bullets = []
        
        for sentence in raw_sentences[:8]:
            # Strip leading hyphens or bullets that might come from the model
            clean_s = re.sub(r"^[\s\-\*\u2022]+", "", sentence).strip()
            if not clean_s:
                continue
            # Capitalize first letter
            if len(clean_s) > 1:
                clean_s = clean_s[0].upper() + clean_s[1:]
            elif len(clean_s) == 1:
                clean_s = clean_s.upper()

            formatted_bullets.append(f"- {clean_s}")
            
        return "\n".join(formatted_bullets)

    # For paragraphs, also try to capitalize the first letter
    if len(normalized_summary) > 1:
        return normalized_summary[0].upper() + normalized_summary[1:]
    return normalized_summary.upper()
