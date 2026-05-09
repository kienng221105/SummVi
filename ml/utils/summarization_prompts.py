def summarize_prompt(text: str) -> str:
    return f"Tóm tắt: {text}"

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
