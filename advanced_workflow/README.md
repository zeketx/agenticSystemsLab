# AI News Aggregator

Content aggregation system that collects AI-related content from YouTube channels and blogs, with optional transcript fetching and scheduled automation.

## Features

✅ **Multi-Source Aggregation**
- YouTube channels (RSS feeds + transcripts)
- Blog articles (Anthropic Research & Engineering)
- YAML-based configuration

✅ **Automated Collection**
- 24-hour scheduling ready
- Configurable filters (YouTube/blogs/transcripts)
- JSON output for downstream processing

✅ **Database Storage**
- PostgreSQL with automatic deduplication
- Docker containerization
- Optional database save via `--save-to-db` flag

✅ **Content Enrichment**
- Backfill transcripts for videos in database
- Extract full article content as markdown
- Batch processing with rate limiting
- Idempotent enrichment (safe to re-run)
- Error tracking and retry management

🚧 **Planned**
- LLM-powered content summarization
- Email digest delivery

## Tech Stack

**Core:** Python 3.11+, Pydantic, BeautifulSoup4, feedparser, youtube-transcript-api, markdownify
**Database:** PostgreSQL 16 (Docker), SQLAlchemy
**Deployment:** Render (cron scheduling)
**Storage:** JSON export + PostgreSQL (with deduplication and enrichment tracking)

## Project Structure

```
app/
├── __main__.py              # CLI entry point (with subcommands)
├── commands/                # CLI commands
│   ├── __init__.py
│   └── enrich.py            # Content enrichment command
├── config/                  # YAML config loader + validation
├── database/                # Database layer
│   ├── connections.py       # Database connection
│   ├── models.py            # SQLAlchemy table definitions
│   ├── repository.py        # Content save operations
│   └── enrichment_repository.py  # Enrichment operations
├── models/                  # Pydantic data models
│   ├── aggregated_content.py
│   └── transcript.py
├── scrapers/                # Content scrapers
│   ├── youtube_scraper.py   # RSS + metadata
│   └── anthropic_scraper.py # Blog scraping
└── services/                # Business logic
    ├── orchestrator.py      # Main aggregation coordinator
    ├── youtube_transcript.py # Transcript fetching
    ├── article_content_fetcher.py  # Article HTML → Markdown
    └── content_enrichment.py # Enrichment orchestrator

config/
└── sources.yaml             # Source configuration

scripts/
├── init.sql                 # Database schema (with enrichment)
└── enrichment_migration.sql # Migration for existing databases

docker-compose.yml           # PostgreSQL container
```

## Quick Start

### Installation

```bash
# Clone and install dependencies
git clone <repo>
cd advanced_workflow
pip install -e .

# Configure sources (optional)
nano config/sources.yaml
```

### Database Setup (Optional)

```bash
# Start PostgreSQL container
docker-compose up -d

# Verify database is running
docker ps

# Database will auto-initialize with schema from scripts/init.sql
# Default credentials: newsagg/newsagg/newsagg (user/password/database)

# For existing databases, run enrichment migration
docker cp scripts/enrichment_migration.sql news-aggregator-db:/tmp/
docker exec news-aggregator-db psql -U newsagg -d newsagg -f /tmp/enrichment_migration.sql
```

### Usage

#### Content Aggregation

```bash
# Full aggregation (with transcripts) - backward compatible
python -m app

# Or use explicit aggregate command
python -m app aggregate

# Fast mode (no transcripts - 21x faster!)
python -m app aggregate --no-transcripts

# Save to file
python -m app aggregate --output results.json

# Quiet mode for cron jobs
python -m app aggregate --quiet --no-transcripts --output /path/to/daily.json

# YouTube or blogs only
python -m app aggregate --no-blogs          # YouTube only
python -m app aggregate --no-youtube        # Blogs only

# Save to database (requires Docker setup)
python -m app aggregate --no-transcripts --save-to-db

# Custom config
python -m app aggregate --config /path/to/sources.yaml
```

#### Content Enrichment

```bash
# Show enrichment statistics
python -m app enrich --stats

# Dry run (preview what will be enriched)
python -m app enrich --dry-run

# Enrich all unenriched content (videos + articles)
python -m app enrich

# Enrich videos only
python -m app enrich --videos-only

# Enrich articles only
python -m app enrich --articles-only

# Limit number of items to enrich
python -m app enrich --limit 50

# Adjust rate limiting (seconds between requests)
python -m app enrich --rate-limit 2.0

# Custom batch size
python -m app enrich --batch-size 25

# Quiet mode for automation
python -m app enrich --quiet
```

### Configuration

Edit `config/sources.yaml`:

```yaml
youtube:
  channels:
    - id: "UC_x36zCEGilGpB1m-V4gmjg"
      name: "IndyDevDan"
      enabled: true
      max_results: 15

blogs:
  anthropic:
    enabled: true
    sources:
      - url: "https://www.anthropic.com/research"
        type: "research"
        max_results: 20
```

## Performance

| Mode | Time | Use Case |
|------|------|----------|
| With transcripts | ~18s | Full content analysis |
| No transcripts | ~1s | Quick aggregation |
| Blogs only | ~0.6s | Articles only |

**Recommendation:** Use `--no-transcripts` for scheduled runs unless you specifically need transcript data.

## Development Status

**✅ Stage 1: Content Aggregation (Complete)**
- YouTube RSS scraping + transcript fetching
- Anthropic blog scraping
- CLI with filtering options
- YAML configuration
- JSON export
- PostgreSQL storage with automatic deduplication

**✅ Stage 2: Content Enrichment (Complete)**
- Backfill video transcripts from database
- Extract full article content as markdown
- Batch processing with rate limiting
- Idempotent enrichment operations
- Error tracking and retry management
- Enrichment statistics and dry-run mode

**🚧 Stage 3: Next Phase**
- LLM-powered content summarization
- Email digest delivery
- Additional blog sources (OpenAI, DeepMind, etc.)

## Workflow

### Typical Usage Pattern

1. **Aggregate new content** (daily via cron):
   ```bash
   python -m app aggregate --save-to-db --no-transcripts --quiet
   ```

2. **Enrich database content** (periodic backfill):
   ```bash
   python -m app enrich --quiet
   ```

3. **Check enrichment status**:
   ```bash
   python -m app enrich --stats
   ```

This two-stage approach keeps aggregation fast while allowing comprehensive content enrichment to run separately.
