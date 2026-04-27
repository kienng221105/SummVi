import re
from hashlib import md5
from typing import Iterable


def normalize_whitespace(text: str) -> str:
    """
    Chuẩn hóa khoảng trắng: thay thế nhiều spaces/tabs/newlines liên tiếp thành 1 space.
    """
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """
    Làm sạch văn bản: chuẩn hóa whitespace và loại bỏ spaces thừa trước dấu câu.
    Ví dụ: "Hello  ,  world !" -> "Hello, world!"
    """
    normalized = normalize_whitespace(text)
    normalized = re.sub(r"[ \t]+([,.!?;:])", r"\1", normalized)
    return normalized.strip()


def split_sentences(text: str) -> list[str]:
    """
    Tách văn bản thành các câu riêng biệt.

    Logic:
    - Split sau dấu câu (. ! ?) + space
    - Hoặc split theo newline
    - Regex lookbehind (?<=...) để giữ dấu câu trong kết quả
    """
    normalized = clean_text(text)
    if not normalized:
        return []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", normalized)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def recursive_chunk_text(text: str, chunk_size: int = 160, overlap: int = 32) -> list[str]:
    """
    Chia văn bản thành các chunks với overlap để giữ context giữa các chunks.

    Args:
        text: Văn bản cần chia
        chunk_size: Số từ tối đa mỗi chunk
        overlap: Số từ overlap giữa các chunks liên tiếp

    Logic:
    - Nếu văn bản ngắn hơn chunk_size: trả về 1 chunk duy nhất
    - Nếu dài hơn: chia thành nhiều chunks với sliding window
    - Overlap giúp model không bỏ lỡ thông tin ở ranh giới chunks
    """
    normalized = clean_text(text)
    words = normalized.split()
    if not words:
        return []

    if len(words) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)

    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(words):
            break

    return chunks


def lead_sentences_summary(text: str, max_sentences: int = 3, ratio: float = 0.35) -> str:
    """
    Tạo tóm tắt extractive đơn giản bằng cách lấy các câu đầu tiên.

    Phương pháp:
    - Lấy tối đa max_sentences câu đầu tiên
    - Hoặc lấy đến khi đạt max_length (tính theo ratio * độ dài văn bản gốc)
    - Điều kiện nào đạt trước thì dừng

    Đây là fallback method khi không có GPU hoặc model lỗi.
    """
    sentences = split_sentences(text)
    if not sentences:
        return clean_text(text)

    max_length = max(120, int(len(clean_text(text)) * ratio))
    selected: list[str] = []
    current_length = 0

    for sentence in sentences:
        selected.append(sentence)
        current_length += len(sentence) + 1
        if len(selected) >= max_sentences or current_length >= max_length:
            break

    return clean_text(" ".join(selected))[:max_length].strip()


def safe_ratio(numerator: float, denominator: float) -> float:
    """
    Tính tỷ lệ an toàn, tránh chia cho 0.
    """
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def hashed_vector(tokens: Iterable[str], dimensions: int = 384) -> list[float]:
    """
    Tạo pseudo-embedding vector từ tokens bằng hash-based method.

    Logic:
    - Hash mỗi token thành một số nguyên
    - Map số đó vào một index trong vector (modulo dimensions)
    - Tăng giá trị tại index đó lên 1
    - Normalize vector về unit length

    Đây là fallback khi không có SentenceTransformer model.
    Không có semantic meaning nhưng đủ để làm similarity search cơ bản.
    """
    vector = [0.0] * dimensions
    token_count = 0

    for token in tokens:
        hashed = int(md5(token.encode("utf-8")).hexdigest(), 16)
        index = hashed % dimensions
        vector[index] += 1.0
        token_count += 1

    if token_count == 0:
        return vector

    # Normalize về unit vector
    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [value / norm for value in vector]
