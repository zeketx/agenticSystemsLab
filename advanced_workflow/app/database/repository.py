"""Database repository for saving content with deduplication."""

import logging
from sqlalchemy import text
from app.scrapers import VideoData, ArticleData
from app.database.connections import engine

logger = logging.getLogger(__name__)


def save_video(video: VideoData) -> bool:
    """
    Upsert video to database - skip if already exists.

    Args:
        video: VideoData object to save

    Returns:
        True if inserted, False if skipped (duplicate)
    """
    try:
        with engine.connect() as conn:
            # Extract transcript text if available
            transcript_text = None
            if video.transcript and video.transcript.is_available:
                transcript_text = video.transcript.transcript_text

            result = conn.execute(text("""
                INSERT INTO videos (
                    video_id, title, channel_name, channel_id,
                    published_at, link, description, transcript_text
                )
                VALUES (
                    :video_id, :title, :channel_name, :channel_id,
                    :published_date, :link, :description, :transcript_text
                )
                ON CONFLICT (video_id) DO NOTHING
                RETURNING id
            """), {
                "video_id": video.video_id,
                "title": video.title,
                "channel_name": video.channel_name,
                "channel_id": video.channel_id,
                "published_date": video.published_date,
                "link": str(video.link),
                "description": video.description,
                "transcript_text": transcript_text
            })
            conn.commit()

            # Check if row was inserted
            return result.rowcount > 0

    except Exception as e:
        logger.error(f"Error saving video {video.video_id}: {e}")
        return False


def save_article(article: ArticleData) -> bool:
    """
    Upsert article to database - skip if already exists.

    Args:
        article: ArticleData object to save

    Returns:
        True if inserted, False if skipped (duplicate)
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO articles (
                    url, title, slug, published_at, summary, subjects
                )
                VALUES (
                    :url, :title, :slug, :published_date, :summary, :subject_tags
                )
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            """), {
                "url": article.url,
                "title": article.title,
                "slug": article.slug,
                "published_date": article.published_date,
                "summary": article.summary,
                "subject_tags": article.subject_tags if article.subject_tags else []
            })
            conn.commit()

            # Check if row was inserted
            return result.rowcount > 0

    except Exception as e:
        logger.error(f"Error saving article {article.url}: {e}")
        return False


def save_all(videos: list[VideoData], articles: list[ArticleData]) -> dict:
    """
    Save all content to database with deduplication.

    Args:
        videos: List of VideoData objects
        articles: List of ArticleData objects

    Returns:
        Dictionary with stats: videos_saved, articles_saved, videos_skipped, articles_skipped
    """
    v_saved = 0
    v_skipped = 0

    for video in videos:
        if save_video(video):
            v_saved += 1
        else:
            v_skipped += 1

    a_saved = 0
    a_skipped = 0

    for article in articles:
        if save_article(article):
            a_saved += 1
        else:
            a_skipped += 1

    return {
        "videos_saved": v_saved,
        "videos_skipped": v_skipped,
        "articles_saved": a_saved,
        "articles_skipped": a_skipped,
        "total_saved": v_saved + a_saved,
        "total_skipped": v_skipped + a_skipped
    }
