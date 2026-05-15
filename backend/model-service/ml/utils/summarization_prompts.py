LENGTH_POLICY = {
    "short": {"ratio": 0.08, "min": 40,  "max": 80,  "min_new": 16,  "length_penalty": 0.4},
    "medium": {"ratio": 0.22, "min": 128, "max": 256, "min_new": 64,  "length_penalty": 1.0},
    "long": {"ratio": 0.45, "min": 256, "max": 512, "min_new": 160, "length_penalty": 1.5},
}

STYLE_PREFIX_MAP = {
    "bullet": "[TIN_GACH_DAU_DONG]",
    "paragraph": "[TIN_DOAN_VAN]",
}

STYLE_INSTRUCTION_MAP = {
    "bullet": "Tóm tắt thành các gạch đầu dòng ngắn gọn.",
    "paragraph": "Tóm tắt thành một đoạn văn mạch lạc.",
    "keypoints": "Liệt kê các điểm chính quan trọng nhất.",
}

LENGTH_INSTRUCTION_MAP = {
    "short": "Tóm tắt cực ngắn gọn trong 1-2 câu, chỉ giữ ý chính quan trọng nhất.",
    "medium": "Tóm tắt vừa phải, giữ đầy đủ các ý quan trọng.",
    "long": "Tóm tắt chi tiết và đầy đủ, giữ tối đa thông tin quan trọng, bao gồm cả ngữ cảnh và các chi tiết hỗ trợ.",
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
    min_new_tokens = max(min_new_tokens, 1)

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
    """
    Tạo prompt với instruction rõ ràng cho model biết
    cần tóm tắt ngắn/vừa/dài và theo format nào.

    ViT5 fine-tuned trên vietnews dùng prefix "summarize: "
    nên ta thêm instruction vào trước text.
    """
    length_instruction = LENGTH_INSTRUCTION_MAP.get(summary_length, LENGTH_INSTRUCTION_MAP["medium"])
    style_instruction = STYLE_INSTRUCTION_MAP.get(style, STYLE_INSTRUCTION_MAP["paragraph"])

    prompt = f"summarize: {length_instruction} {style_instruction}\n{text}"
    return prompt

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
