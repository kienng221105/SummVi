from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, GUID
from app.core.timezone import get_now


class Message(Base):
    __tablename__ = "messages"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")
