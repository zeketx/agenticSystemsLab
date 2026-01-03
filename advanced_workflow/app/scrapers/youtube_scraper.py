"""YouTube RSS feed scraper for fetching latest videos from channels."""

import feedparser
import requests
import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl

from app.models.transcript import TranscriptData


class VideoData(BaseModel):
    """YouTube video metadata with validation."""

    title: str = Field(..., min_length=1, max_length=500, description="Video title")
    video_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{11}$', description="11-character YouTube video ID")
    channel_name: str = Field(..., min_length=1, max_length=200, description="Channel display name")
    channel_id: str = Field(..., pattern=r'^UC[a-zA-Z0-9_-]{22}$', description="YouTube channel ID (UC prefix + 22 chars)")
    published_date: datetime
    link: HttpUrl = Field(..., description="Full YouTube video URL")
    description: str = Field(default="", description="Video description")
    transcript: Optional[TranscriptData] = Field(default=None, description="Video transcript if available")

    @field_validator('link')
    @classmethod
    def validate_youtube_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure link is a valid YouTube URL."""
        url_str = str(v)
        if not ('youtube.com' in url_str or 'youtu.be' in url_str):
            raise ValueError('Link must be a valid YouTube URL')
        return v

    @field_validator('title', 'channel_name')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace."""
        return v.strip()

    model_config = {
        'str_strip_whitespace': True,
        'validate_assignment': True,
    }


class YouTubeScraper:
    """Scraper for fetching YouTube videos via RSS feeds."""

    RSS_BASE_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="

    @staticmethod
    def get_channel_id_from_handle(handle: str) -> str:
        """
        Get YouTube channel ID from @handle.

        Args:
            handle: YouTube handle (with or without @)

        Returns:
            Channel ID string
        """
        handle = handle.replace("@", "")
        url = f"https://www.youtube.com/@{handle}"

        try:
            response = requests.get(url)
            response.raise_for_status()

            patterns = [
                r'"channelId":"(UC[a-zA-Z0-9_-]{22})"',
                r'"externalId":"(UC[a-zA-Z0-9_-]{22})"',
                r'channel/(UC[a-zA-Z0-9_-]{22})'
            ]

            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    return match.group(1)

            raise ValueError(f"Could not find channel ID for @{handle}")

        except Exception as e:
            raise Exception(f"Error fetching channel ID: {str(e)}")

    @staticmethod
    def fetch_videos(channel_id: str, max_results: int = 15) -> List[VideoData]:
        """Fetch latest videos from a YouTube channel using RSS feed."""
        rss_url = f"{YouTubeScraper.RSS_BASE_URL}{channel_id}"

        try:
            feed = feedparser.parse(rss_url)

            if feed.bozo:
                raise ValueError(f"Failed to parse RSS feed: {feed.bozo_exception}")

            videos = []

            for entry in feed.entries[:max_results]:
                video_id = entry.yt_videoid if hasattr(entry, 'yt_videoid') else entry.id.split(':')[-1]
                published = datetime(*entry.published_parsed[:6])

                video = VideoData(
                    title=entry.title,
                    video_id=video_id,
                    channel_name=entry.author if hasattr(entry, 'author') else feed.feed.title,
                    channel_id=channel_id,
                    published_date=published,
                    link=entry.link,
                    description=entry.summary if hasattr(entry, 'summary') else ""
                )

                videos.append(video)

            return videos

        except Exception as e:
            raise Exception(f"Error fetching videos from channel {channel_id}: {str(e)}")
