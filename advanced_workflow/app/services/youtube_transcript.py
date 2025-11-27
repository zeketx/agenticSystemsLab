"""YouTube transcript fetching service."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)


def get_transcript(video_id: str) -> str:
    """Fetch transcript for a YouTube video."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_data = ytt_api.fetch(video_id)
        transcript_text = " ".join(segment.text for segment in transcript_data)
        return transcript_text

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return "No transcript available"
    except Exception:
        return "No transcript available"
