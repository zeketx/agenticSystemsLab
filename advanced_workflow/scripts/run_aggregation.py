#!/usr/bin/env python3
"""CLI script for running content aggregation from all configured sources."""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Union

from dotenv import load_dotenv

from app.models import AggregatedContent
from app.scrapers import ArticleData, VideoData
from app.services.orchestrator import ContentAggregator


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging for the script.

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def display_summary(aggregated: AggregatedContent) -> None:
    """
    Display human-readable summary of aggregated content.

    Args:
        aggregated: AggregatedContent object with metadata and content
    """
    metadata = aggregated.metadata

    print("\n" + "=" * 70)
    print("  CONTENT AGGREGATION RUN SUMMARY")
    print("=" * 70)

    # Run info
    print(f"\nRun ID:      {metadata.run_id}")
    print(f"Started:     {metadata.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Completed:   {metadata.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:    {metadata.duration_seconds:.2f} seconds")

    # Summary stats
    print(f"\n{'SUMMARY':=^70}")
    print(f"Total Items:         {metadata.total_items}")
    print(f"  - YouTube Videos:  {metadata.videos_count}")
    print(f"  - Blog Articles:   {metadata.articles_count}")
    print(f"\nSources Attempted:   {metadata.sources_attempted}")
    print(f"Sources Succeeded:   {metadata.sources_succeeded}")
    print(f"Success Rate:        {metadata.success_rate:.1f}%")

    # Errors
    if metadata.has_errors:
        print(f"\n{'ERRORS':=^70}")
        print(f"Total Errors: {len(metadata.errors)}")
        for i, error in enumerate(metadata.errors, 1):
            print(f"  {i}. {error}")

    # Recent content preview
    if aggregated.has_content:
        print(f"\n{'RECENT CONTENT (Top 10)':=^70}")
        for i, item in enumerate(aggregated.all_content[:10], 1):
            item_type = "VIDEO" if isinstance(item, VideoData) else "ARTICLE"
            source = item.channel_name if isinstance(item, VideoData) else item.source_type.capitalize()
            date_str = item.published_date.strftime('%Y-%m-%d')

            print(f"{i:2d}. [{item_type:7s}] {item.title[:50]:<50s}")
            print(f"     Source: {source:<30s} Date: {date_str}")
    else:
        print(f"\n{'NO CONTENT':=^70}")
        print("No content was aggregated during this run.")

    print("\n" + "=" * 70 + "\n")


def export_to_json(aggregated: AggregatedContent, output_path: str) -> None:
    """
    Export aggregated content to JSON file.

    Args:
        aggregated: AggregatedContent object to export
        output_path: Path where JSON file should be saved
    """
    output_file = Path(output_path)

    # Create parent directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Export using Pydantic's model serialization
    json_data = aggregated.model_dump_json(indent=2)

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_data)

    print(f"Exported aggregated content to: {output_file.absolute()}")


def main() -> int:
    """
    Main entry point for aggregation runner.

    Returns:
        Exit code: 0 (success), 1 (partial failure), 2 (total failure)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="AI News Aggregator - Fetch content from configured sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default configuration
  python scripts/run_aggregation.py

  # Run with custom config and export to JSON
  python scripts/run_aggregation.py --config-path /path/to/config.yaml --output-json /tmp/result.json

  # Fetch only YouTube videos with verbose logging
  python scripts/run_aggregation.py --youtube-only --verbose

  # Fetch only blog articles
  python scripts/run_aggregation.py --blogs-only
        """
    )

    parser.add_argument(
        '--config-path',
        type=str,
        default=None,
        help='Path to sources.yaml configuration file (default: config/sources.yaml)'
    )

    parser.add_argument(
        '--output-json',
        type=str,
        default=None,
        help='Export aggregated content to JSON file at specified path'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging output'
    )

    parser.add_argument(
        '--youtube-only',
        action='store_true',
        help='Fetch only YouTube videos (skip blogs)'
    )

    parser.add_argument(
        '--blogs-only',
        action='store_true',
        help='Fetch only blog articles (skip YouTube)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Load environment variables
    load_dotenv()
    logger.debug("Environment variables loaded")

    # Validate mutually exclusive options
    if args.youtube_only and args.blogs_only:
        logger.error("Cannot specify both --youtube-only and --blogs-only")
        return 2

    # Determine what to include
    include_youtube = not args.blogs_only
    include_blogs = not args.youtube_only

    try:
        # Run aggregation
        logger.info("Starting content aggregation...")
        aggregated = ContentAggregator.aggregate_content(
            config_path=args.config_path,
            include_youtube=include_youtube,
            include_blogs=include_blogs
        )

        # Display summary
        display_summary(aggregated)

        # Export to JSON if requested
        if args.output_json:
            export_to_json(aggregated, args.output_json)

        # Determine exit code based on results
        if aggregated.metadata.total_items == 0:
            logger.warning("No content was aggregated")
            return 1  # Partial failure

        if aggregated.metadata.has_errors:
            logger.warning(f"Completed with {len(aggregated.metadata.errors)} error(s)")
            return 1  # Partial failure

        logger.info("Aggregation completed successfully")
        return 0  # Success

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        return 2  # Total failure

    except Exception as e:
        logger.exception(f"Aggregation failed with unexpected error: {e}")
        return 2  # Total failure


if __name__ == "__main__":
    sys.exit(main())
