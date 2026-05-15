from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.models.user import AppUser
from app.schemas.ai import (
    FileSummarizeResponse,
    MessageResponse,
    MultiSummarizeRequest,
    SummarizeRequest,
    SummarizeResponse,
)
from app.services import ai_service, document_service
from fastapi import UploadFile, File, Query


from starlette.concurrency import run_in_threadpool
from fastapi import HTTPException, status

router = APIRouter()


@router.post("/", response_model=SummarizeResponse)
async def post_summarize(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Authenticated summarization endpoint với conversation tracking.

    Features:
    - Lưu conversation history
    - Track user activity
    - Auto cleanup old conversations

    Run trong threadpool để không block async event loop.
    """
    return await run_in_threadpool(ai_service.summarize_text, db, current_user.id, request)


@router.post("/multi", response_model=SummarizeResponse)
async def post_multi_summarize(
    request: MultiSummarizeRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Multi-document summarization endpoint.
    Tóm tắt nhiều đoạn văn bản cùng lúc thành một bản tóm tắt duy nhất.
    """
    return await run_in_threadpool(ai_service.multi_summarize_text, db, current_user.id, request)


@router.post("/summarize-file", response_model=FileSummarizeResponse)
async def post_summarize_file(
    file: UploadFile = File(...),
    summary_length: str = Query(default="medium", pattern="^(short|medium|long)$"),
    output_format: str = Query(default="paragraph", pattern="^(paragraph|bullet|keypoints)$"),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    File summarization endpoint.
    Upload file (PDF, DOCX, TXT) và model service sẽ trích xuất + tóm tắt.
    """
    # Validate file extension
    allowed_extensions = {".pdf", ".docx", ".txt"}
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file {ext} không hỗ trợ. Chỉ chấp nhận .pdf, .docx, .txt"
        )

    # Validate file size (20MB limit)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File quá lớn. Giới hạn tối đa là 20MB."
        )

    from app.services.model_client import ModelServiceError, model_client

    try:
        result = await run_in_threadpool(
            model_client.summarize_file,
            content,
            file.filename,
            summary_length,
            output_format,
        )
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service is unavailable",
        ) from exc

    return FileSummarizeResponse(
        summary=result.get("summary", ""),
        extracted_text_preview=result.get("extracted_text_preview"),
        diagnostics=result.get("diagnostics", {}),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_history(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Lấy messages của một conversation.
    Security: chỉ trả về nếu conversation thuộc về current_user.
    """
    return ai_service.get_messages_for_user(db, conversation_id, current_user.id)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Trích xuất văn bản từ tài liệu (PDF, Word, TXT) với giới hạn 5000 từ.
    """
    # 1. Validate file extension
    allowed_extensions = {".pdf", ".docx", ".txt"}
    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file {ext} không hỗ trợ. Chỉ chấp nhận .pdf, .docx, .txt"
        )

    # 2. Validate file size (20MB limit)
    MAX_FILE_SIZE = 20 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File quá lớn. Giới hạn tối đa là 20MB."
        )
    
    # Reset file pointer after reading for extraction
    await file.seek(0)
    
    text = await run_in_threadpool(document_service.extract_text_from_file, file)
    
    return {
        "filename": file.filename,
        "content": text,
        "word_count": len(text.split())
    }


@router.get("/model-health")
async def model_health():
    """
    Kiểm tra trạng thái model service.
    """
    from app.services.model_client import ModelServiceError, model_client

    try:
        result = await run_in_threadpool(model_client.health_check)
    except ModelServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service is unavailable",
        )
    return result
