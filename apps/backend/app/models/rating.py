from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, GUID
from app.core.timezone import get_now


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), nullable=False, unique=True, index=True)
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)

    user = relationship("AppUser", back_populates="ratings")
    conversation = relationship("Conversation", back_populates="rating")
