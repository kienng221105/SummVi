from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def get_user_conversations(db: Session, user_id: UUID):
    """
    Lấy danh sách conversations của user, sắp xếp theo thời gian cập nhật gần nhất.
    """
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def delete_conversation(db: Session, conversation_id: UUID, user_id: UUID) -> bool:
    """
    Xóa một conversation của user.

    Security:
    - Filter theo cả conversation_id VÀ user_id để đảm bảo user chỉ xóa được conversation của mình
    - Trả về False nếu không tìm thấy conversation (hoặc không có quyền)
    """
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if conversation is None:
        return False

    db.delete(conversation)
    db.commit()
    return True
