"""YouTube transcript fetching service."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


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


def get_transcript(video_id: str, return_model: bool = True) -> TranscriptData | str:
    """
    Fetch transcript for a YouTube video.

    Args:
        video_id: YouTube video ID (11 characters)
        return_model: If True, return TranscriptData model; if False, return plain string (backward compatible)

    Returns:
        TranscriptData model with transcript and metadata, or plain string if return_model=False
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_data = ytt_api.fetch(video_id)
        transcript_text = " ".join(segment.text for segment in transcript_data)

        if return_model:
            return TranscriptData(
                video_id=video_id,
                transcript_text=transcript_text,
                char_count=len(transcript_text),
                word_count=len(transcript_text.split()),
                is_available=True
            )
        else:
            # Backward compatible mode
            return transcript_text

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        error_msg = f"Transcript unavailable: {str(e)}"
        if return_model:
            return TranscriptData(
                video_id=video_id,
                transcript_text="No transcript available",
                char_count=0,
                word_count=0,
                is_available=False,
                error_message=error_msg
            )
        else:
            return "No transcript available"

    except Exception as e:
        error_msg = f"Error fetching transcript: {str(e)}"
        if return_model:
            return TranscriptData(
                video_id=video_id,
                transcript_text="No transcript available",
                char_count=0,
                word_count=0,
                is_available=False,
                error_message=error_msg
            )
        else:
            return "No transcript available"
