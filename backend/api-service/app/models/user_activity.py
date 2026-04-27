from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text

from app.core.database import Base, GUID
from app.core.timezone import get_now


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)
