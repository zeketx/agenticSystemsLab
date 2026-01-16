"""Database repository for content enrichment operations."""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from app.database.connections import engine

logger = logging.getLogger(__name__)


def get_unenriched_videos(limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Query videos without transcripts that haven't been attempted yet.

    Args:
        limit: Maximum number of videos to return
        offset: Number of videos to skip (for pagination)

    Returns:
        List of dicts with: id, video_id, title, link
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, video_id, title, link
                FROM videos
                WHERE transcript_text IS NULL
                  AND transcript_fetch_attempted = FALSE
                ORDER BY published_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset})

            return [dict(row._mapping) for row in result]

    except Exception as e:
        logger.error(f"Error querying unenriched videos: {e}")
        return []


def get_unenriched_articles(limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Query articles without content_markdown that haven't been attempted yet.

    Args:
        limit: Maximum number of articles to return
        offset: Number of articles to skip (for pagination)

    Returns:
        List of dicts with: id, url, title
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, url, title
                FROM articles
                WHERE content_markdown IS NULL
                  AND content_fetch_attempted = FALSE
                ORDER BY published_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": offset})

            return [dict(row._mapping) for row in result]

    except Exception as e:
        logger.error(f"Error querying unenriched articles: {e}")
        return []


def update_video_transcript(
    video_id: int,
    transcript_text: Optional[str],
    success: bool,
    error_message: Optional[str] = None
) -> bool:
    """
    Update video with transcript and enrichment metadata.

    Args:
        video_id: Database ID of the video
        transcript_text: Transcript text (if success)
        success: Whether transcript fetch succeeded
        error_message: Error message (if failure)

    Returns:
        True if update succeeded, False otherwise

    Sets:
        - transcript_text (if success)
        - transcript_enriched_at (if success)
        - transcript_fetch_attempted = True
        - transcript_fetch_error (if failure)
    """
    try:
        with engine.connect() as conn:
            if success:
                conn.execute(text("""
                    UPDATE videos
                    SET transcript_text = :transcript_text,
                        transcript_enriched_at = :enriched_at,
                        transcript_fetch_attempted = TRUE,
                        transcript_fetch_error = NULL
                    WHERE id = :video_id
                """), {
                    "video_id": video_id,
                    "transcript_text": transcript_text,
                    "enriched_at": datetime.now()
                })
            else:
                conn.execute(text("""
                    UPDATE videos
                    SET transcript_fetch_attempted = TRUE,
                        transcript_fetch_error = :error_message
                    WHERE id = :video_id
                """), {
                    "video_id": video_id,
                    "error_message": error_message
                })

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"Error updating video {video_id}: {e}")
        return False


def update_article_content(
    article_id: int,
    content_markdown: Optional[str],
    success: bool,
    error_message: Optional[str] = None
) -> bool:
    """
    Update article with markdown content and enrichment metadata.

    Args:
        article_id: Database ID of the article
        content_markdown: Full article content in markdown (if success)
        success: Whether content fetch succeeded
        error_message: Error message (if failure)

    Returns:
        True if update succeeded, False otherwise

    Sets:
        - content_markdown (if success)
        - content_enriched_at (if success)
        - content_fetch_attempted = True
        - content_fetch_error (if failure)
    """
    try:
        with engine.connect() as conn:
            if success:
                conn.execute(text("""
                    UPDATE articles
                    SET content_markdown = :content_markdown,
                        content_enriched_at = :enriched_at,
                        content_fetch_attempted = TRUE,
                        content_fetch_error = NULL
                    WHERE id = :article_id
                """), {
                    "article_id": article_id,
                    "content_markdown": content_markdown,
                    "enriched_at": datetime.now()
                })
            else:
                conn.execute(text("""
                    UPDATE articles
                    SET content_fetch_attempted = TRUE,
                        content_fetch_error = :error_message
                    WHERE id = :article_id
                """), {
                    "article_id": article_id,
                    "error_message": error_message
                })

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"Error updating article {article_id}: {e}")
        return False


def get_enrichment_stats() -> dict:
    """
    Get statistics about enrichment progress.

    Returns:
        Dictionary with enrichment statistics for videos and articles:
        {
            'videos': {
                'total': int,
                'with_transcript': int,
                'without_transcript': int,
                'enrichment_pending': int,
                'enrichment_failed': int
            },
            'articles': {
                'total': int,
                'with_content': int,
                'without_content': int,
                'enrichment_pending': int,
                'enrichment_failed': int
            }
        }
    """
    try:
        with engine.connect() as conn:
            # Video statistics
            video_stats = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(transcript_text) as with_transcript,
                    COUNT(*) FILTER (WHERE transcript_text IS NULL) as without_transcript,
                    COUNT(*) FILTER (WHERE transcript_text IS NULL AND transcript_fetch_attempted = FALSE) as enrichment_pending,
                    COUNT(*) FILTER (WHERE transcript_text IS NULL AND transcript_fetch_attempted = TRUE) as enrichment_failed
                FROM videos
            """)).fetchone()

            # Article statistics
            article_stats = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(content_markdown) as with_content,
                    COUNT(*) FILTER (WHERE content_markdown IS NULL) as without_content,
                    COUNT(*) FILTER (WHERE content_markdown IS NULL AND content_fetch_attempted = FALSE) as enrichment_pending,
                    COUNT(*) FILTER (WHERE content_markdown IS NULL AND content_fetch_attempted = TRUE) as enrichment_failed
                FROM articles
            """)).fetchone()

            return {
                'videos': {
                    'total': video_stats.total,
                    'with_transcript': video_stats.with_transcript,
                    'without_transcript': video_stats.without_transcript,
                    'enrichment_pending': video_stats.enrichment_pending,
                    'enrichment_failed': video_stats.enrichment_failed
                },
                'articles': {
                    'total': article_stats.total,
                    'with_content': article_stats.with_content,
                    'without_content': article_stats.without_content,
                    'enrichment_pending': article_stats.enrichment_pending,
                    'enrichment_failed': article_stats.enrichment_failed
                }
            }

    except Exception as e:
        logger.error(f"Error getting enrichment stats: {e}")
        return {
            'videos': {'total': 0, 'with_transcript': 0, 'without_transcript': 0, 'enrichment_pending': 0, 'enrichment_failed': 0},
            'articles': {'total': 0, 'with_content': 0, 'without_content': 0, 'enrichment_pending': 0, 'enrichment_failed': 0}
        }
