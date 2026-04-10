from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base, GUID
from app.core.timezone import get_now


class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(512), nullable=False)
    vector_collection_id = Column(String(255), nullable=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    embedding_model = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_now, nullable=False)

    conversation = relationship("Conversation", back_populates="documents")
