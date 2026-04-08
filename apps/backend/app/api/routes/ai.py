from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.models.user import AppUser
from app.schemas.ai import MessageResponse, SummarizeRequest, SummarizeResponse
from app.services import ai_service


router = APIRouter()


@router.post("/", response_model=SummarizeResponse)
def post_summarize(
    request: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    return ai_service.summarize_text(db, current_user.id, request)


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_history(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    return ai_service.get_messages_for_user(db, conversation_id, current_user.id)
