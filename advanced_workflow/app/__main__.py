"""Entry point: python -m app"""

import argparse
import logging
import sys
from pathlib import Path
from app.services import ContentAggregator


def main() -> int:
    """Main entry point for content aggregation."""
    parser = argparse.ArgumentParser(
        description="Aggregate content from configured sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app                          # Run full aggregation
  python -m app --output results.json    # Save to file
  python -m app --no-transcripts         # Skip transcript fetching
  python -m app --quiet --output out.json # Quiet mode for cron jobs
        """
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to sources.yaml config file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--no-youtube",
        action="store_true",
        help="Skip YouTube video fetching"
    )
    parser.add_argument(
        "--no-blogs",
        action="store_true",
        help="Skip blog article fetching"
    )
    parser.add_argument(
        "--no-transcripts",
        action="store_true",
        help="Skip transcript fetching for videos"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging"
    )

    args = parser.parse_args()

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


if __name__ == "__main__":
    sys.exit(main())
