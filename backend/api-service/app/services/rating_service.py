from uuid import UUID

from sqlalchemy.orm import Session

from app.models.rating import Rating
from app.schemas.rating import RatingCreate


def create_rating(db: Session, user_id: UUID, rating_data: RatingCreate) -> Rating:
    """
    Tạo hoặc cập nhật rating cho một conversation.

    Logic:
    - Nếu conversation đã có rating: cập nhật rating và feedback
    - Nếu chưa có: tạo mới
    - Upsert pattern đảm bảo mỗi conversation chỉ có 1 rating duy nhất
    """
    rating = db.query(Rating).filter(Rating.conversation_id == rating_data.conversation_id).first()
    if rating is None:
        rating = Rating(
            user_id=user_id,
            conversation_id=rating_data.conversation_id,
            rating=rating_data.rating,
            feedback=rating_data.feedback,
        )
        db.add(rating)
    else:
        rating.rating = rating_data.rating
        rating.feedback = rating_data.feedback

    db.commit()
    db.refresh(rating)
    return rating


def get_rating(db: Session, conversation_id: UUID) -> Rating | None:
    """Lấy rating của một conversation, trả về None nếu chưa có rating."""
    return db.query(Rating).filter(Rating.conversation_id == conversation_id).first()
