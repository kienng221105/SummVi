import io

import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile


def extract_text_from_file(file: UploadFile, word_limit: int = 5000) -> str:
    """
    Extract text from uploaded PDF, DOCX, or TXT files.
    """
    filename = (file.filename or "").lower()
    content = ""

    try:
        if filename.endswith(".pdf"):
            content = _extract_from_pdf(file)
        elif filename.endswith(".docx"):
            content = _extract_from_docx(file)
        elif filename.endswith(".txt"):
            content = _extract_from_txt(file)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Use .pdf, .docx, or .txt.",
            )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Error processing file: {exc}") from exc

    words = content.split()
    if len(words) > word_limit:
        content = " ".join(words[:word_limit])

    return content.strip()


def _extract_from_pdf(file: UploadFile) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    file_bytes = file.file.read()
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def _extract_from_docx(file: UploadFile) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "DOCX support requires the python-docx package. "
                "Install backend/api-service/requirements.txt and restart the service."
            ),
        ) from exc

    file_bytes = file.file.read()
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs)


def _extract_from_txt(file: UploadFile) -> str:
    """
    Extract text from a TXT file.
    Tries UTF-8 first, then falls back to latin-1 on decode errors.
    """
    file_bytes = file.file.read()
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")
