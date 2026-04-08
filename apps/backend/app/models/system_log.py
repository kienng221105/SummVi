from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base, GUID


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(GUID(), primary_key=True, index=True, default=uuid4)
    request_id = Column(String(64), index=True, nullable=False)
    endpoint = Column(String(255), nullable=False)
    route_name = Column(String(255), nullable=True)
    method = Column(String(16), nullable=False)
    log_level = Column(String(16), nullable=False, default="INFO")
    status_code = Column(Integer, nullable=False)
    response_time = Column(Integer, nullable=True)
    user_id = Column(GUID(), nullable=True)
    client_ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    error_type = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
