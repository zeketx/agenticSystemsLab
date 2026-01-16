"""Entry point: python -m app"""

import argparse
import logging
import sys
from pathlib import Path
from app.services import ContentAggregator
from app.commands import enrich


def setup_aggregate_parser(subparsers) -> None:
    """Setup content aggregation command parser."""
    aggregate_parser = subparsers.add_parser(
        'aggregate',
        help='Aggregate content from configured sources',
        description='Fetch and aggregate content from YouTube channels and blogs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app aggregate                          # Run full aggregation
  python -m app aggregate --output results.json    # Save to file
  python -m app aggregate --no-transcripts         # Skip transcript fetching
  python -m app aggregate --quiet --output out.json # Quiet mode for cron jobs
        """
    )
    aggregate_parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to sources.yaml config file"
    )
    aggregate_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    aggregate_parser.add_argument(
        "--no-youtube",
        action="store_true",
        help="Skip YouTube video fetching"
    )
    aggregate_parser.add_argument(
        "--no-blogs",
        action="store_true",
        help="Skip blog article fetching"
    )
    aggregate_parser.add_argument(
        "--no-transcripts",
        action="store_true",
        help="Skip transcript fetching for videos"
    )
    aggregate_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging"
    )
    aggregate_parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="Save results to database"
    )

    aggregate_parser.set_defaults(func=run_aggregate)


def run_aggregate(args) -> int:
    """Execute content aggregation command."""
    # Configure logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    try:
        # Run aggregation
        result = ContentAggregator.aggregate_content(
            config_path=args.config,
            include_youtube=not args.no_youtube,
            include_blogs=not args.no_blogs,
            include_transcripts=not args.no_transcripts,
        )

        # Save to database if requested
        if args.save_to_db:
            from app.database.repository import save_all
            stats = save_all(result.videos, result.articles)
            logging.info(
                f"Database save complete: {stats['total_saved']} saved, "
                f"{stats['total_skipped']} skipped (duplicates)"
            )

        # Output results
        json_output = result.model_dump_json(indent=2)

        if args.output:
            Path(args.output).write_text(json_output)
            if not args.quiet:
                print(f"Results written to {args.output}")
        else:
            print(json_output)

        # Return exit code based on errors
        return 1 if result.metadata.has_errors else 0

    except Exception as e:
        logging.error(f"Aggregation failed: {e}", exc_info=not args.quiet)
        return 1


def main() -> int:
    """Main entry point with subcommand support."""
    parser = argparse.ArgumentParser(
        description="AI News Aggregator - Content collection and enrichment system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  aggregate    Fetch content from YouTube channels and blogs
  enrich       Backfill transcripts and article content in database

Examples:
  python -m app aggregate --save-to-db       # Aggregate and save to database
  python -m app enrich --stats               # Show enrichment statistics
  python -m app enrich --dry-run             # Preview enrichment without changes
  python -m app enrich --articles-only       # Enrich only articles
        """
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='COMMAND'
    )

    # Setup aggregation command
    setup_aggregate_parser(subparsers)

    # Setup enrichment command
    enrich.setup_enrich_parser(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, default to aggregate for backward compatibility
    if args.command is None:
        # Re-parse with aggregate as default
        sys.argv.insert(1, 'aggregate')
        args = parser.parse_args()

    # Execute the command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
