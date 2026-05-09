def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator

def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."

def is_empty(text: str) -> bool:
    return not text or not text.strip()

def word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0
