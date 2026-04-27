from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.core.database import Base, GUID
from app.core.timezone import get_now


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=get_now, nullable=False, onupdate=get_now)

    user = relationship("AppUser", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="conversation", cascade="all, delete-orphan")
    rating = relationship("Rating", back_populates="conversation", cascade="all, delete-orphan", uselist=False)
