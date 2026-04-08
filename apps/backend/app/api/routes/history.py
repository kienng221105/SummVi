from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.models.user import AppUser
from app.schemas.ai import ConversationResponse
from app.services import history_service


router = APIRouter()


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    return history_service.get_user_conversations(db, current_user.id)


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    success = history_service.delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hội thoại")
    return {"message": "Đã xóa thành công"}
