from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    conversation_id: UUID
    rating: int = Field(..., ge=1, le=5)
    feedback: str | None = None


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    conversation_id: UUID
    rating: int
    feedback: str | None
    created_at: datetime
