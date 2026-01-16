"""Content enrichment orchestrator for backfilling transcripts and article content."""

import logging
import time
from typing import Optional
from app.database import enrichment_repository
from app.services.youtube_transcript import get_transcript
from app.services.article_content_fetcher import fetch_article_content

logger = logging.getLogger(__name__)


def enrich_videos(
    batch_size: int = 50,
    max_items: Optional[int] = None,
    rate_limit_seconds: float = 0.5
) -> dict:
    """
    Enrich videos with missing transcripts.

    Args:
        batch_size: Number of videos to process in each batch
        max_items: Maximum number of videos to enrich (None = all)
        rate_limit_seconds: Delay between API calls

    Returns:
        {
            'processed': int,
            'succeeded': int,
            'failed': int,
            'errors': list[str]
        }

    Process:
        1. Query batch of unenriched videos
        2. For each video:
            a. Call get_transcript(video_id)
            b. Update database with result
            c. Log progress
            d. Sleep for rate limiting
        3. Continue until no more unenriched videos or max_items reached
    """
    logger.info("Starting video enrichment process")

    processed = 0
    succeeded = 0
    failed = 0
    errors = []
    offset = 0

    while True:
        # Check if we've hit the max items limit
        if max_items and processed >= max_items:
            logger.info(f"Reached max items limit: {max_items}")
            break

        # Query batch of unenriched videos
        batch_limit = batch_size
        if max_items:
            batch_limit = min(batch_size, max_items - processed)

        videos = enrichment_repository.get_unenriched_videos(limit=batch_limit, offset=offset)

        if not videos:
            logger.info("No more unenriched videos found")
            break

        logger.info(f"Processing batch of {len(videos)} videos (offset: {offset})")

        for video in videos:
            video_id = video['video_id']
            db_id = video['id']
            title = video['title']

            try:
                # Fetch transcript
                logger.debug(f"Fetching transcript for video: {title} ({video_id})")
                transcript_data = get_transcript(video_id, return_model=True)

                if transcript_data.is_available:
                    # Update database with success
                    success = enrichment_repository.update_video_transcript(
                        video_id=db_id,
                        transcript_text=transcript_data.transcript_text,
                        success=True
                    )

                    if success:
                        succeeded += 1
                        logger.info(f"✓ Enriched video: {title[:50]}... ({transcript_data.word_count} words)")
                    else:
                        failed += 1
                        error_msg = f"Database update failed for video: {title}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    # Transcript not available, mark as attempted with error
                    enrichment_repository.update_video_transcript(
                        video_id=db_id,
                        transcript_text=None,
                        success=False,
                        error_message=transcript_data.error_message
                    )
                    failed += 1
                    error_msg = f"Transcript unavailable for: {title} - {transcript_data.error_message}"
                    errors.append(error_msg)
                    logger.warning(f"✗ {error_msg}")

            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Error processing video {title}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

                enrichment_repository.update_video_transcript(
                    video_id=db_id,
                    transcript_text=None,
                    success=False,
                    error_message=str(e)
                )
                failed += 1

            processed += 1

            # Rate limiting
            if rate_limit_seconds > 0 and processed < (max_items or float('inf')):
                time.sleep(rate_limit_seconds)

        # Move offset forward for next batch
        offset += batch_size

    logger.info(f"Video enrichment complete: {processed} processed, {succeeded} succeeded, {failed} failed")

    return {
        'processed': processed,
        'succeeded': succeeded,
        'failed': failed,
        'errors': errors
    }


def enrich_articles(
    batch_size: int = 50,
    max_items: Optional[int] = None,
    rate_limit_seconds: float = 1.5
) -> dict:
    """
    Enrich articles with missing content.

    Args:
        batch_size: Number of articles to process in each batch
        max_items: Maximum number of articles to enrich (None = all)
        rate_limit_seconds: Delay between HTTP requests

    Returns:
        {
            'processed': int,
            'succeeded': int,
            'failed': int,
            'errors': list[str]
        }

    Process:
        1. Query batch of unenriched articles
        2. For each article:
            a. Call fetch_article_content(url)
            b. Update database with result
            c. Log progress
            d. Sleep for rate limiting
        3. Continue until no more unenriched articles or max_items reached
    """
    logger.info("Starting article enrichment process")

    processed = 0
    succeeded = 0
    failed = 0
    errors = []
    offset = 0

    while True:
        # Check if we've hit the max items limit
        if max_items and processed >= max_items:
            logger.info(f"Reached max items limit: {max_items}")
            break

        # Query batch of unenriched articles
        batch_limit = batch_size
        if max_items:
            batch_limit = min(batch_size, max_items - processed)

        articles = enrichment_repository.get_unenriched_articles(limit=batch_limit, offset=offset)

        if not articles:
            logger.info("No more unenriched articles found")
            break

        logger.info(f"Processing batch of {len(articles)} articles (offset: {offset})")

        for article in articles:
            url = article['url']
            db_id = article['id']
            title = article['title']

            try:
                # Fetch article content
                logger.debug(f"Fetching content for article: {title}")
                content_markdown, error_message = fetch_article_content(url)

                if content_markdown and not error_message:
                    # Update database with success
                    success = enrichment_repository.update_article_content(
                        article_id=db_id,
                        content_markdown=content_markdown,
                        success=True
                    )

                    if success:
                        succeeded += 1
                        content_length = len(content_markdown)
                        logger.info(f"✓ Enriched article: {title[:50]}... ({content_length} chars)")
                    else:
                        failed += 1
                        error_msg = f"Database update failed for article: {title}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                else:
                    # Content fetch failed, mark as attempted with error
                    enrichment_repository.update_article_content(
                        article_id=db_id,
                        content_markdown=None,
                        success=False,
                        error_message=error_message
                    )
                    failed += 1
                    error_msg = f"Content fetch failed for: {title} - {error_message}"
                    errors.append(error_msg)
                    logger.warning(f"✗ {error_msg}")

            except Exception as e:
                # Handle unexpected errors
                error_msg = f"Error processing article {title}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

                enrichment_repository.update_article_content(
                    article_id=db_id,
                    content_markdown=None,
                    success=False,
                    error_message=str(e)
                )
                failed += 1

            processed += 1

            # Rate limiting
            if rate_limit_seconds > 0 and processed < (max_items or float('inf')):
                time.sleep(rate_limit_seconds)

        # Move offset forward for next batch
        offset += batch_size

    logger.info(f"Article enrichment complete: {processed} processed, {succeeded} succeeded, {failed} failed")

    return {
        'processed': processed,
        'succeeded': succeeded,
        'failed': failed,
        'errors': errors
    }


def enrich_all(
    videos_batch_size: int = 50,
    articles_batch_size: int = 50,
    max_videos: Optional[int] = None,
    max_articles: Optional[int] = None,
    video_rate_limit: float = 0.5,
    article_rate_limit: float = 1.5
) -> dict:
    """
    Enrich both videos and articles.

    Args:
        videos_batch_size: Batch size for video processing
        articles_batch_size: Batch size for article processing
        max_videos: Maximum videos to enrich (None = all)
        max_articles: Maximum articles to enrich (None = all)
        video_rate_limit: Seconds between video API calls
        article_rate_limit: Seconds between article HTTP requests

    Returns:
        {
            'videos': enrich_videos() result,
            'articles': enrich_articles() result
        }
    """
    logger.info("Starting full content enrichment (videos + articles)")

    video_results = enrich_videos(
        batch_size=videos_batch_size,
        max_items=max_videos,
        rate_limit_seconds=video_rate_limit
    )

    article_results = enrich_articles(
        batch_size=articles_batch_size,
        max_items=max_articles,
        rate_limit_seconds=article_rate_limit
    )

    logger.info("Full content enrichment complete")

    return {
        'videos': video_results,
        'articles': article_results
    }
