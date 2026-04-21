import re
import unicodedata
VIET_CHARS = (
    "aăâbcdđeêghiklmnoôơpqrstuưvxyAĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXY"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)
ALLOWED_CHARS = re.compile(
    rf"[^\w\s\.,!?;:()\-–—\"\'«»{re.escape(VIET_CHARS)}]"
)
def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = remove_headers_footers(text)
    text = remove_ocr_artifacts(text)
    text = normalize_whitespace(text)
    return text

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def remove_headers_footers(text: str) -> str:
    lines = text.split("\n")
    line_freq: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped:
            line_freq[stripped] = line_freq.get(stripped, 0) + 1
    repeated = {line for line, count in line_freq.items() if count >= 3}
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\s*(trang\s*)?\d+\s*$", stripped, re.IGNORECASE):
            continue
        if stripped in repeated:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def remove_ocr_artifacts(text: str) -> str:
    text = ALLOWED_CHARS.sub(" ", text)
    text = re.sub(r"[.]{4,}", "...", text)
    text = re.sub(r"[-]{3,}", "—", text)
    text = re.sub(r"[_]{3,}", " ", text)
    text = re.sub(r"^\s*[^\w\sđĐ]\s*$", "", text, flags=re.MULTILINE)
    return text

def normalize_whitespace(text: str) -> str:
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\t+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def merge_pages(pages) -> str:
    parts = []
    for p in pages:
        if p.text.strip():
            parts.append(f"[TRANG {p.page_num}]\n{p.text.strip()}")
    return "\n\n".join(parts)