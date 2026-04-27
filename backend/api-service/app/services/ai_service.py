from time import perf_counter
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user_activity import UserActivity
from app.schemas.ai import SummarizeRequest, SummarizeResponse
from app.services import analytics_service
from app.services.inference_log_service import create_inference_log
from app.services.model_client import ModelServiceError, model_client


def create_conversation(db: Session, user_id: UUID, title: str | None) -> Conversation:
    """Tạo conversation mới cho user."""
    conversation = Conversation(user_id=user_id, title=title or "Tóm tắt văn bản")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def create_message(db: Session, conversation_id: UUID, content: str, is_user: bool) -> Message:
    """
    Tạo message trong conversation.
    is_user=True: tin nhắn từ user, is_user=False: tin nhắn từ AI assistant
    """
    message = Message(conversation_id=conversation_id, content=content, is_user=is_user)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages(db: Session, conversation_id: UUID):
    """Lấy tất cả messages trong conversation, sắp xếp theo thời gian."""
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def get_messages_for_user(db: Session, conversation_id: UUID, user_id: UUID):
    """
    Lấy messages của conversation với security check.
    Chỉ trả về messages nếu conversation thuộc về user.
    """
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
    Xóa các conversations cũ nhất nếu user có quá nhiều conversations.

    Logic:
    - Giữ lại {limit} conversations mới nhất
    - Xóa tất cả conversations cũ hơn
    - Giúp tránh database bloat và giữ UI gọn gàng
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
    """
    API chính để tạo tóm tắt với conversation tracking.

    Flow:
    1. Tìm hoặc tạo conversation
    2. Lưu user message vào conversation
    3. Gọi summarization service để tạo summary
    4. Lưu assistant message (summary) vào conversation
    5. Log user activity
    6. Cleanup old conversations nếu tạo mới

    Returns:
        SummarizeResponse với summary, metrics, và conversation_id
    """
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

    started_at = perf_counter()
    try:
        result = model_client.summarize(
            request.text,
            summary_length=request.summary_length,
            output_format=request.output_format,
        )
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model service is unavailable",
        ) from exc

    summary = str(result.get("summary") or "")
    metrics = result.get("metrics") or {}
    diagnostics = result.get("diagnostics") or {}
    latency = float(diagnostics.get("latency") or (perf_counter() - started_at))

    assistant_message = create_message(db, conversation.id, summary, is_user=False)

    create_inference_log(
        db,
        input_length=len(request.text),
        summary_length=len(summary),
        input_word_count=int(metrics.get("input_word_count", 0)),
        summary_word_count=int(metrics.get("summary_word_count", 0)),
        length_ratio=float(metrics.get("length_ratio", 0.0)),
        compression_ratio=float(metrics.get("compression_ratio", 0.0)),
        latency=latency,
        diagnostics=diagnostics,
    )

    import threading
    threading.Thread(
        target=analytics_service.record_analytics,
        kwargs={"summary": summary, "input_text": request.text},
        daemon=True,
    ).start()

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
        summary=summary,
        metrics=metrics,
        created_at=assistant_message.created_at,
    )
