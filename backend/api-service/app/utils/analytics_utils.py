"""
Lightweight analytics utilities for the BI layer.
Extracts keywords (word frequency) and assigns topics via rule-based mapping.
"""

import json
import re
from collections import Counter
from typing import List

VIETNAMESE_STOP_WORDS = frozenset(
    [
        "và", "của", "là", "có", "được", "cho", "trong", "này", "với",
        "các", "một", "để", "không", "những", "đã", "theo", "từ", "về",
        "khi", "đến", "tại", "cũng", "còn", "nhiều", "như", "nếu", "đó",
        "sẽ", "thì", "do", "vì", "bị", "lại", "ra", "rồi", "nên", "đang",
        "hơn", "sau", "trên", "hay", "phải", "rất", "vào", "qua", "mà",
        "người", "năm", "ông", "bà", "anh", "chị", "em", "tôi", "chúng",
        "họ", "nó", "ai", "gì", "nào", "đây", "kia", "ấy",
    ]
)

TOPIC_KEYWORDS = {
    "Công nghệ": [
        "công nghệ", "phần mềm", "trí tuệ nhân tạo", "AI", "máy tính",
        "internet", "dữ liệu", "robot", "blockchain", "điện tử",
        "ứng dụng", "lập trình", "thuật toán", "mạng", "server",
    ],
    "Y tế": [
        "sức khỏe", "y tế", "bệnh viện", "bác sĩ", "thuốc",
        "dịch bệnh", "vaccine", "virus", "covid", "điều trị",
        "y học", "phẫu thuật", "bệnh nhân", "lâm sàng",
    ],
    "Chính trị": [
        "chính phủ", "chính trị", "quốc hội", "bầu cử", "đảng",
        "luật", "pháp luật", "ngoại giao", "chính sách", "lãnh đạo",
        "cải cách", "nghị quyết", "đại biểu",
    ],
    "Kinh tế": [
        "kinh tế", "tài chính", "ngân hàng", "thị trường", "cổ phiếu",
        "đầu tư", "lạm phát", "GDP", "xuất khẩu", "nhập khẩu",
        "doanh nghiệp", "thương mại", "tiền tệ",
    ],
    "Giáo dục": [
        "giáo dục", "trường học", "sinh viên", "học sinh", "đại học",
        "giáo viên", "đào tạo", "thi cử", "bằng cấp", "nghiên cứu",
        "học bổng", "giảng dạy",
    ],
    "Thể thao": [
        "thể thao", "bóng đá", "cầu thủ", "giải đấu", "huy chương",
        "olympic", "đội tuyển", "huấn luyện", "trận đấu", "vô địch",
        "thành tích", "thi đấu",
    ],
    "Văn hóa": [
        "văn hóa", "nghệ thuật", "âm nhạc", "phim", "sách",
        "triển lãm", "di sản", "truyền thống", "lễ hội", "ca sĩ",
        "đạo diễn", "sáng tạo",
    ],
}


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    if not text or not text.strip():
        return []

    words = re.findall(r"\b\w+\b", text.lower())
    filtered = [w for w in words if w not in VIETNAMESE_STOP_WORDS and len(w) > 1]
    most_common = Counter(filtered).most_common(top_k)
    return [word for word, _ in most_common]


def assign_topic(text: str) -> str:
    if not text or not text.strip():
        return "Tổng hợp"

    lower_text = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in lower_text)
        if score > 0:
            scores[topic] = score

    if not scores:
        return "Tổng hợp"

    return max(scores, key=scores.get)


def keywords_to_json(keywords: List[str]) -> str:
    return json.dumps(keywords, ensure_ascii=False)


def keywords_from_json(raw: str) -> List[str]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
