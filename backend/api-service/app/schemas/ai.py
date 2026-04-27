from datetime import datetime
from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SummarizeRequest(BaseModel):
    text: str | None = Field(default=None, description="Vietnamese text to summarize")
    custom_content: str | None = Field(default=None, description="Compatibility field from legacy project")
    summary_length: str = Field(default="medium", pattern="^(short|medium|long)$")
    output_format: str = Field(default="paragraph", pattern="^(paragraph|bullet|keypoints)$")
    conversation_title: str | None = None
    conversation_id: UUID | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        content = (self.custom_content or self.text or "").strip()
        if not content:
            raise ValueError("text or custom_content is required")
        self.custom_content = content
        self.text = content
        return self


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    content: str
    is_user: bool
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class SummarizeResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    content: str
    summary: str
    metrics: Dict[str, float]
    created_at: datetime
