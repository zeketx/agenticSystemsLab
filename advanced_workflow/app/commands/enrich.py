"""Enrichment CLI command for backfilling transcripts and article content."""

import argparse
import logging
import sys
from app.database import enrichment_repository
from app.services import content_enrichment

logger = logging.getLogger(__name__)


def setup_enrich_parser(subparsers) -> None:
    """
    Setup enrichment command parser.

    Usage:
        python -m app enrich [options]
    """
    enrich_parser = subparsers.add_parser(
        'enrich',
        help='Enrich database content with transcripts and article content',
        description='Backfill missing transcripts for videos and full content for articles in the database.'
    )

    # Content type filters
    enrich_parser.add_argument(
        '--videos-only',
        action='store_true',
        help='Only enrich video transcripts'
    )
    enrich_parser.add_argument(
        '--articles-only',
        action='store_true',
        help='Only enrich article content'
    )

    # Limits
    enrich_parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of items to enrich per content type (default: all)'
    )
    enrich_parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of items to process in each batch (default: 50)'
    )

    # Rate limiting
    enrich_parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Seconds to wait between requests (default: 1.0)'
    )

    # Safety and information
    enrich_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be enriched without making changes'
    )
    enrich_parser.add_argument(
        '--stats',
        action='store_true',
        help='Show enrichment statistics and exit'
    )

    # Quiet mode
    enrich_parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output (errors still shown)'
    )

    enrich_parser.set_defaults(func=run_enrich)


def run_enrich(args) -> int:
    """
    Execute enrichment command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Configure logging
    if args.quiet:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Handle --stats flag
    if args.stats:
        return show_stats()

    # Handle --dry-run flag
    if args.dry_run:
        return run_dry_run(args)

    # Determine what to enrich
    enrich_videos_flag = not args.articles_only
    enrich_articles_flag = not args.videos_only

    logger.info("=" * 60)
    logger.info("Content Enrichment Process")
    logger.info("=" * 60)

    # Run enrichment
    try:
        if enrich_videos_flag and enrich_articles_flag:
            # Enrich both
            logger.info("Enriching both videos and articles...")
            results = content_enrichment.enrich_all(
                videos_batch_size=args.batch_size,
                articles_batch_size=args.batch_size,
                max_videos=args.limit,
                max_articles=args.limit,
                video_rate_limit=args.rate_limit,
                article_rate_limit=args.rate_limit
            )

            # Display results
            logger.info("\n" + "=" * 60)
            logger.info("VIDEO ENRICHMENT RESULTS")
            logger.info("=" * 60)
            _display_results(results['videos'])

            logger.info("\n" + "=" * 60)
            logger.info("ARTICLE ENRICHMENT RESULTS")
            logger.info("=" * 60)
            _display_results(results['articles'])

        elif enrich_videos_flag:
            # Enrich videos only
            logger.info("Enriching videos only...")
            results = content_enrichment.enrich_videos(
                batch_size=args.batch_size,
                max_items=args.limit,
                rate_limit_seconds=args.rate_limit
            )

            logger.info("\n" + "=" * 60)
            logger.info("VIDEO ENRICHMENT RESULTS")
            logger.info("=" * 60)
            _display_results(results)

        else:
            # Enrich articles only
            logger.info("Enriching articles only...")
            results = content_enrichment.enrich_articles(
                batch_size=args.batch_size,
                max_items=args.limit,
                rate_limit_seconds=args.rate_limit
            )

            logger.info("\n" + "=" * 60)
            logger.info("ARTICLE ENRICHMENT RESULTS")
            logger.info("=" * 60)
            _display_results(results)

        logger.info("\n" + "=" * 60)
        logger.info("Enrichment complete!")
        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.warning("\nEnrichment interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        return 1


def show_stats() -> int:
    """
    Display enrichment statistics and exit.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        stats = enrichment_repository.get_enrichment_stats()

        print("\n" + "=" * 60)
        print("ENRICHMENT STATISTICS")
        print("=" * 60)

        print("\nVIDEOS:")
        print(f"  Total videos:              {stats['videos']['total']}")
        print(f"  With transcripts:          {stats['videos']['with_transcript']}")
        print(f"  Without transcripts:       {stats['videos']['without_transcript']}")
        print(f"  Enrichment pending:        {stats['videos']['enrichment_pending']}")
        print(f"  Enrichment failed:         {stats['videos']['enrichment_failed']}")

        print("\nARTICLES:")
        print(f"  Total articles:            {stats['articles']['total']}")
        print(f"  With full content:         {stats['articles']['with_content']}")
        print(f"  Without full content:      {stats['articles']['without_content']}")
        print(f"  Enrichment pending:        {stats['articles']['enrichment_pending']}")
        print(f"  Enrichment failed:         {stats['articles']['enrichment_failed']}")

        print("\n" + "=" * 60)

        return 0

    except Exception as e:
        print(f"Error fetching statistics: {e}", file=sys.stderr)
        return 1


def run_dry_run(args) -> int:
    """
    Show what would be enriched without making changes.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        enrich_videos_flag = not args.articles_only
        enrich_articles_flag = not args.videos_only

        print("\n" + "=" * 60)
        print("DRY RUN - No changes will be made")
        print("=" * 60)

        if enrich_videos_flag:
            # Query unenriched videos
            limit = args.limit if args.limit else 100
            videos = enrichment_repository.get_unenriched_videos(limit=limit)

            print(f"\nVIDEOS TO ENRICH: {len(videos)}")
            if videos:
                print("\nSample videos (first 5):")
                for video in videos[:5]:
                    print(f"  - {video['title'][:60]}... ({video['video_id']})")

                if len(videos) > 5:
                    print(f"  ... and {len(videos) - 5} more")

        if enrich_articles_flag:
            # Query unenriched articles
            limit = args.limit if args.limit else 100
            articles = enrichment_repository.get_unenriched_articles(limit=limit)

            print(f"\nARTICLES TO ENRICH: {len(articles)}")
            if articles:
                print("\nSample articles (first 5):")
                for article in articles[:5]:
                    print(f"  - {article['title'][:60]}...")

                if len(articles) > 5:
                    print(f"  ... and {len(articles) - 5} more")

        print("\n" + "=" * 60)
        print("Run without --dry-run to perform enrichment")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"Error during dry run: {e}", file=sys.stderr)
        return 1


def _display_results(results: dict) -> None:
    """
    Display enrichment results in a formatted way.

    Args:
        results: Results dictionary from enrichment function
    """
    print(f"Processed: {results['processed']}")
    print(f"Succeeded: {results['succeeded']}")
    print(f"Failed:    {results['failed']}")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more errors")
