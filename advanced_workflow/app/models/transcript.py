"""YouTube transcript data model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TranscriptData(BaseModel):
    """YouTube video transcript data with metadata."""

    video_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{11}$', description="11-character YouTube video ID")
    transcript_text: str = Field(..., min_length=1, description="Full transcript text")
    fetched_at: datetime = Field(default_factory=datetime.now, description="Timestamp when transcript was fetched")
    char_count: int = Field(ge=0, description="Character count of transcript")
    word_count: int = Field(ge=0, description="Approximate word count")
    is_available: bool = Field(default=True, description="Whether transcript was successfully fetched")
    error_message: Optional[str] = Field(default=None, description="Error message if transcript unavailable")

    @field_validator('transcript_text')
    @classmethod
    def validate_transcript_not_empty(cls, v: str) -> str:
        """Ensure transcript is not just whitespace."""
        if not v or not v.strip():
            raise ValueError('Transcript text cannot be empty or whitespace-only')
        return v.strip()

    model_config = {
        'str_strip_whitespace': True,
        'validate_assignment': True,
    }
