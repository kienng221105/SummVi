LENGTH_POLICY = {
    # max_new_tokens is a ceiling, not a target. These caps are intentionally
    # lower for short/medium so the model is forced to produce visibly different
    # lengths. Long keeps the old safe 512-token behavior.
    "short": {"ratio": 0.08, "min": 64, "max": 80, "min_new": 16, "length_penalty": 0.6},
    "medium": {"ratio": 0.22, "min": 192, "max": 256, "min_new": 120, "length_penalty": 1.1},
    "long": {"ratio": 0.40, "min": 384, "max": 512, "min_new": 160, "length_penalty": 1.2},
}

STYLE_PREFIX_MAP = {
    "bullet": "[TIN_GACH_DAU_DONG]",
    "paragraph": "[TIN_DOAN_VAN]",
}

STYLE_INSTRUCTION_MAP = {
    "bullet": "Tóm tắt thành các gạch đầu dòng ngắn gọn.",
    "paragraph": "Tóm tắt thành một đoạn văn mạch lạc.",
}

LENGTH_INSTRUCTION_MAP = {
    "short": "Tóm tắt ngắn gọn, chỉ giữ các ý chính quan trọng nhất.",
    "medium": "Tóm tắt vừa phải, giữ đầy đủ các ý quan trọng.",
    "long": "Tóm tắt chi tiết, giữ tối đa thông tin quan trọng nhưng tránh lan man.",
}


def generation_policy_for_length(
    input_tokens: int,
    summary_length: str = "medium",
    style: str = "paragraph",
) -> dict[str, float | int]:
    policy = LENGTH_POLICY.get(summary_length, LENGTH_POLICY["medium"])
    max_new_tokens = int(input_tokens * policy["ratio"])
    max_new_tokens = max(max_new_tokens, int(policy["min"]))
    max_new_tokens = min(max_new_tokens, int(policy["max"]))

    if style == "bullet":
        max_new_tokens = int(max_new_tokens * 1.10)
        max_new_tokens = min(max_new_tokens, int(policy["max"]))

    min_new_tokens = min(int(policy["min_new"]), max_new_tokens - 1)

    return {
        "max_new_tokens": max_new_tokens,
        "min_new_tokens": min_new_tokens,
        "length_penalty": float(policy["length_penalty"]),
    }


def max_new_tokens_for_length(
    input_tokens: int,
    summary_length: str = "medium",
    style: str = "paragraph",
) -> int:
    return int(
        generation_policy_for_length(
            input_tokens=input_tokens,
            summary_length=summary_length,
            style=style,
        )["max_new_tokens"]
    )


def summarize_prompt(
    text: str,
    style: str = "paragraph",
    summary_length: str = "medium",
) -> str:
    # Keep the model input identical to the old working setup.
    # The currently loaded ViT5 summarization model hallucinates when we prepend
    # instruction text such as "Tóm tắt:" or style prefixes. Length is controlled
    # by max_new_tokens, and bullet formatting is handled after generation.
    return text

def qa_prompt(context: str, question: str) -> str:
    return (
        f"Dựa vào văn bản sau, trả lời câu hỏi.\n"
        f"Câu hỏi: {question}\n"
        f"Văn bản: {context}"
    )

def community_prompt(entities: str, relations: str) -> str:
    return f"Thực thể: {entities}\nQuan hệ: {relations}"

def meta_summary_prompt(labeled_summaries: str) -> str:
    return (
        f"Tóm tắt nội dung chính của từng tài liệu sau:\n"
        f"{labeled_summaries}"
    )
