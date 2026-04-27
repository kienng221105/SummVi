from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.core.database import Base, GUID
from app.core.timezone import get_now


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    topic = Column(String(128), nullable=False, default="General", index=True)
    keywords = Column(Text, nullable=False, default="[]")  # JSON-encoded list
    summary_length = Column(Integer, nullable=False)
    compression_ratio = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False, index=True)
