from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user_activity import UserActivity
from app.schemas.ai import SummarizeRequest, SummarizeResponse
from app.services.summarization_service import build_summarization_service


def create_conversation(db: Session, user_id: UUID, title: str | None) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title or "Tóm tắt văn bản")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def create_message(db: Session, conversation_id: UUID, content: str, is_user: bool) -> Message:
    message = Message(conversation_id=conversation_id, content=content, is_user=is_user)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages(db: Session, conversation_id: UUID):
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_messages_for_user(db: Session, conversation_id: UUID, user_id: UUID):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )
    if conversation is None:
        return []
    return get_messages(db, conversation_id)


def cleanup_old_conversations(db: Session, user_id: UUID, limit: int = 10):
    """
    Deletes the oldest conversations for a user if they exceed the limit.
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .offset(limit)
        .all()
    )

    for conversation in conversations:
        db.delete(conversation)
    db.commit()


def summarize_text(db: Session, user_id: UUID, request: SummarizeRequest) -> SummarizeResponse:
    if request.conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == request.conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if conversation is None:
            # Fallback if invalid ID
            conversation = create_conversation(
                db,
                user_id=user_id,
                title=request.conversation_title or (request.text[:60] if request.text else "Tóm tắt văn bản"),
            )
    else:
        conversation = create_conversation(
            db,
            user_id=user_id,
            title=request.conversation_title or (request.text[:60] if request.text else "Tóm tắt văn bản"),
        )
        # Cleanup old ones only when creating a new one
        cleanup_old_conversations(db, user_id, limit=10)

    create_message(db, conversation.id, request.text, is_user=True)

    result = build_summarization_service().summarize(
        request.text,
        summary_length=request.summary_length,
        output_format=request.output_format,
    )
    assistant_message = create_message(db, conversation.id, result.summary, is_user=False)

    db.add(
        UserActivity(
            user_id=user_id,
            action="summarize_text",
            details=f"conversation_id={conversation.id};length={len(request.text)}",
        )
    )
    db.commit()

    return SummarizeResponse(
        id=assistant_message.id,
        conversation_id=conversation.id,
        content=assistant_message.content,
        summary=result.summary,
        metrics=result.metrics,
        created_at=assistant_message.created_at,
    )
