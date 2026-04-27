from typing import Dict

from pydantic import BaseModel, Field, field_validator


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Vietnamese text to summarize")
    summary_length: str = Field(default="medium", pattern="^(short|medium|long)$")
    output_format: str = Field(default="paragraph", pattern="^(paragraph|bullet|keypoints)$")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be empty")
        return normalized


class SummarizeResponse(BaseModel):
    summary: str
    metrics: Dict[str, float]
