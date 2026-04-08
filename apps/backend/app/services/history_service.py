from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def get_user_conversations(db: Session, user_id: UUID):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def delete_conversation(db: Session, conversation_id: UUID, user_id: UUID) -> bool:
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
