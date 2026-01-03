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

🚧 **Planned**
- LLM-powered content summarization
- Email digest delivery

## Tech Stack

**Core:** Python 3.11+, Pydantic, BeautifulSoup4, feedparser, youtube-transcript-api
**Database:** PostgreSQL 16 (Docker), SQLAlchemy
**Deployment:** Render (cron scheduling)
**Storage:** JSON export + PostgreSQL (with deduplication)

## Project Structure

```
app/
├── __main__.py              # CLI entry point
├── db.py                    # Database operations (PostgreSQL)
├── config/                  # YAML config loader + validation
├── models/                  # Pydantic data models
│   ├── aggregated_content.py
│   └── transcript.py
├── scrapers/                # Content scrapers
│   ├── youtube_scraper.py   # RSS + metadata
│   └── anthropic_scraper.py # Blog scraping
└── services/                # Business logic
    ├── orchestrator.py      # Main aggregation coordinator
    └── youtube_transcript.py

config/
└── sources.yaml             # Source configuration

scripts/
└── init.sql                 # Database schema

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
```

### Usage

```bash
# Full aggregation (with transcripts)
python -m app

# Fast mode (no transcripts - 21x faster!)
python -m app --no-transcripts

# Save to file
python -m app --output results.json

# Quiet mode for cron jobs
python -m app --quiet --no-transcripts --output /path/to/daily.json

# YouTube or blogs only
python -m app --no-blogs          # YouTube only
python -m app --no-youtube        # Blogs only

# Save to database (requires Docker setup)
python -m app --no-transcripts --save-to-db

# Custom config
python -m app --config /path/to/sources.yaml
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

**✅ Complete**
- YouTube RSS scraping + transcript fetching
- Anthropic blog scraping
- CLI with filtering options
- YAML configuration
- JSON export
- PostgreSQL storage with automatic deduplication

**🚧 Next Phase**
- LLM summarization
- Email delivery
- Additional blog sources (OpenAI, DeepMind, etc.)
