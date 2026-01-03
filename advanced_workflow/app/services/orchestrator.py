"""Content aggregation orchestrator for fetching from all configured sources."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.config import BlogConfig, SourcesConfig, YouTubeChannelConfig, load_sources_config
from app.models import AggregatedContent, AggregationMetadata
from app.scrapers import AnthropicScraper, ArticleData, VideoData, YouTubeScraper
from app.services.youtube_transcript import get_transcript

# Configure logging
logger = logging.getLogger(__name__)


class ContentAggregator:
    """Orchestrates content fetching from all configured sources."""

    @staticmethod
    def aggregate_content(
        config_path: Optional[str] = None,
        include_youtube: bool = True,
        include_blogs: bool = True,
        include_transcripts: bool = True
    ) -> AggregatedContent:
        """
        Fetch content from all configured sources.

        Args:
            config_path: Optional path to sources.yaml (defaults to config/sources.yaml)
            include_youtube: Whether to fetch YouTube videos (default: True)
            include_blogs: Whether to fetch blog articles (default: True)
            include_transcripts: Whether to fetch video transcripts (default: True)

        Returns:
            AggregatedContent object with all fetched content and metadata

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValidationError: If config validation fails
        """
        # Generate unique run ID
        run_id = f"agg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        started_at = datetime.now()

        logger.info(f"Starting content aggregation: {run_id}")

        # Load configuration
        try:
            config = load_sources_config(config_path)
            logger.info(f"Configuration loaded from: {config_path or 'default location'}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

        # Initialize result containers
        all_videos: List[VideoData] = []
        all_articles: List[ArticleData] = []
        all_errors: List[str] = []
        sources_attempted = 0
        sources_succeeded = 0

        # Fetch YouTube videos
        if include_youtube and "channels" in config.youtube:
            channels = config.youtube["channels"]
            enabled_channels = [ch for ch in channels if ch.enabled]

            if enabled_channels:
                logger.info(f"Fetching from {len(enabled_channels)} YouTube channel(s)")
                videos, errors = ContentAggregator._fetch_youtube_videos(
                    enabled_channels,
                    fetch_transcripts=include_transcripts
                )
                all_videos.extend(videos)
                all_errors.extend(errors)
                sources_attempted += len(enabled_channels)
                sources_succeeded += len(enabled_channels) - len(errors)

        # Fetch blog articles
        if include_blogs:
            logger.info(f"Fetching from {len(config.blogs)} blog aggregator(s)")
            articles, errors = ContentAggregator._fetch_blog_articles(config.blogs)
            all_articles.extend(articles)
            all_errors.extend(errors)

            # Count blog sources
            for blog_name, blog_config in config.blogs.items():
                if blog_config.enabled:
                    sources_attempted += len(blog_config.sources)
                    # Count successes (sources - errors for this blog)
                    blog_errors = [e for e in errors if blog_name in e.lower()]
                    sources_succeeded += len(blog_config.sources) - len(blog_errors)

        # Finalize aggregation
        completed_at = datetime.now()
        total_items = len(all_videos) + len(all_articles)

        logger.info(
            f"Aggregation complete: {total_items} items "
            f"({len(all_videos)} videos, {len(all_articles)} articles) "
            f"in {(completed_at - started_at).total_seconds():.2f}s"
        )

        if all_errors:
            logger.warning(f"Encountered {len(all_errors)} error(s) during aggregation")

        # Create metadata
        metadata = AggregationMetadata(
            run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            total_items=total_items,
            videos_count=len(all_videos),
            articles_count=len(all_articles),
            errors=all_errors,
            sources_attempted=sources_attempted,
            sources_succeeded=sources_succeeded,
        )

        # Return aggregated content
        return AggregatedContent(
            metadata=metadata,
            videos=all_videos,
            articles=all_articles,
        )

    @staticmethod
    def _fetch_youtube_videos(
        channels_config: List[YouTubeChannelConfig],
        fetch_transcripts: bool = True
    ) -> Tuple[List[VideoData], List[str]]:
        """
        Fetch videos from configured YouTube channels.

        Args:
            channels_config: List of enabled YouTube channel configurations
            fetch_transcripts: Whether to fetch transcripts for videos (default: True)

        Returns:
            Tuple of (list of VideoData, list of error messages)
        """
        videos: List[VideoData] = []
        errors: List[str] = []

        for channel in channels_config:
            try:
                logger.info(
                    f"Fetching videos from channel: {channel.name} "
                    f"(max_results={channel.max_results})"
                )
                channel_videos = YouTubeScraper.fetch_videos(
                    channel_id=channel.id,
                    max_results=channel.max_results
                )
                videos.extend(channel_videos)
                logger.info(f"Successfully fetched {len(channel_videos)} video(s) from {channel.name}")

            except Exception as e:
                error_msg = f"Failed to fetch videos from channel {channel.name} ({channel.id}): {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Fetch transcripts for all videos if enabled
        if fetch_transcripts and videos:
            logger.info(f"Fetching transcripts for {len(videos)} video(s)")
            for video in videos:
                try:
                    video.transcript = get_transcript(video.video_id)
                    logger.debug(f"Transcript fetched for video {video.video_id}")
                except Exception as e:
                    logger.warning(f"Failed to fetch transcript for {video.video_id}: {e}")
                    # Continue without transcript - not a fatal error

        return videos, errors

    @staticmethod
    def _fetch_blog_articles(
        blogs_config: Dict[str, BlogConfig]
    ) -> Tuple[List[ArticleData], List[str]]:
        """
        Fetch articles from configured blog sources.

        Args:
            blogs_config: Dictionary of blog configurations (keyed by blog name)

        Returns:
            Tuple of (list of ArticleData, list of error messages)
        """
        articles: List[ArticleData] = []
        errors: List[str] = []

        for blog_name, blog_config in blogs_config.items():
            if not blog_config.enabled:
                logger.info(f"Skipping disabled blog: {blog_name}")
                continue

            # Handle Anthropic blog specifically
            if blog_name == "anthropic":
                try:
                    # Determine max_results from config sources
                    max_results = max(
                        (source.max_results for source in blog_config.sources),
                        default=20
                    )

                    logger.info(f"Fetching articles from Anthropic blog (max_results={max_results})")
                    blog_articles = AnthropicScraper.fetch_all_articles(max_results=max_results)
                    articles.extend(blog_articles)
                    logger.info(f"Successfully fetched {len(blog_articles)} article(s) from Anthropic blog")

                except Exception as e:
                    error_msg = f"Failed to fetch articles from Anthropic blog: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Future blog scrapers can be added here
            else:
                logger.warning(
                    f"No scraper implemented for blog '{blog_name}'. "
                    f"Skipping {len(blog_config.sources)} source(s)."
                )
                # Don't count this as an error since it's expected for disabled/future scrapers

        return articles, errors
