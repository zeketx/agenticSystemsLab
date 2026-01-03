"""YouTube transcript fetching service."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
from app.models import TranscriptData


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
