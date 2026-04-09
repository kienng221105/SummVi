import fitz  # PyMuPDF
import docx
from fastapi import UploadFile, HTTPException
import io

def extract_text_from_file(file: UploadFile, word_limit: int = 5000) -> str:
    filename = file.filename.lower()
    content = ""

    try:
        if filename.endswith(".pdf"):
            content = _extract_from_pdf(file)
        elif filename.endswith(".docx"):
            content = _extract_from_docx(file)
        elif filename.endswith(".txt"):
            content = _extract_from_txt(file)
        else:
            raise HTTPException(status_code=400, detail="Định dạng file không hỗ trợ. Vui lòng dùng .pdf, .docx hoặc .txt")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file: {str(e)}")

    # Apply word limit
    words = content.split()
    if len(words) > word_limit:
        content = " ".join(words[:word_limit])
    
    return content.strip()

def _extract_from_pdf(file: UploadFile) -> str:
    file_bytes = file.file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def _extract_from_docx(file: UploadFile) -> str:
    file_bytes = file.file.read()
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([para.text for para in doc.paragraphs])

def _extract_from_txt(file: UploadFile) -> str:
    file_bytes = file.file.read()
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
