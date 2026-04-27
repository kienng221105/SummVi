from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.models.user import AppUser
from app.schemas.ai import MessageResponse, SummarizeRequest, SummarizeResponse
from app.services import ai_service, document_service
from fastapi import UploadFile, File


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
