from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.deps import get_current_active_user, get_db
from app.models.user import AppUser
from app.schemas.rating import RatingCreate, RatingResponse
from app.services import rating_service


router = APIRouter()


@router.post("/", response_model=RatingResponse)
def rate(
    rating_data: RatingCreate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Tạo hoặc cập nhật rating cho conversation.
    Upsert pattern: nếu đã có rating thì update, chưa có thì tạo mới.
    """
    return rating_service.create_rating(db, current_user.id, rating_data)


@router.get("/conversation/{conversation_id}", response_model=RatingResponse)
def get_rate(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_active_user),
):
    """
    Lấy rating của một conversation.
    Trả về 404 nếu conversation chưa có rating.
    """
    rating = rating_service.get_rating(db, conversation_id)
    if rating is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đánh giá")
    return rating
