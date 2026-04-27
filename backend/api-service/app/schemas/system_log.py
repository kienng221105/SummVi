from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SystemLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: str | None
    endpoint: str
    route_name: str | None
    method: str
    log_level: str | None
    status_code: int
    response_time: int | None
    user_id: UUID | None
    client_ip: str | None
    user_agent: str | None
    error_type: str | None
    error_message: str | None
    details: str | None
    created_at: datetime
