# AI News Aggregator - Feature Set Request

## Project Overview

Build an AI-powered news aggregation system that collects content from multiple sources, generates daily LLM-powered summaries, and delivers personalized digests via email.

---

## Core Features

### 1. Content Source Management

#### YouTube Channel Integration
- Maintain a list of YouTube channels to monitor
- Fetch latest videos using YouTube RSS feeds
- Store video metadata and links

#### Blog Post Scraping
- Configure URLs for blog sources (e.g., OpenAI, Anthropic)
- Scrape and parse blog content
- Extract and store article metadata

### 2. Database Structure

**Sources Table:** Store configured content sources (YouTube channels, blog URLs)

**Articles Table:** Store collected content with:
- Article/video title
- Source reference
- Publication date
- Original link
- Raw content/description
- Timestamp

### 3. Daily Digest Generation

- Collect all articles within the specified time frame (24 hours)
- Generate LLM-powered summaries using agent system prompt
- User insights configuration to personalize digest content
- Output format: Short snippets with links to original sources

### 4. Email Delivery

- Send generated daily digest to personal inbox
- Include formatted summaries and source links

### 5. Automation & Scheduling

- Schedule digest generation every 24 hours
- Automatic content fetching and processing
- Automated email delivery

---

## Technical Stack

### Backend
- **Language:** Python 3.11+
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy for database models and table creation
- **Web Scraping:** BeautifulSoup4 for HTML parsing, requests for HTTP
- **Content Parsing:** feedparser for RSS feeds, youtube-transcript-api for transcripts

### Project Structure
```
project-root/
├── app/                          # All application logic
│   ├── agents/                   # SQLAlchemy models
│   ├── services/                 # Business logic (LLM, email)
│   │   └── youtube_transcript.py
│   └── scrapers/                 # Content scrapers
│       ├── youtube_scraper.py    # YouTube RSS feed scraper
│       └── anthropic_scraper.py  # Anthropic blog scraper
├── test_youtube_scraper.py       # YouTube scraper tests
├── test_anthropic_scraper.py     # Anthropic scraper tests
└── docker-compose.yml            # Docker configuration
```

### Infrastructure
- **Containerization:** Docker setup for PostgreSQL
- **Deployment:** Render platform
- **Scheduling:** 24-hour cron/scheduled jobs on Render

---

## Development Phases

### Phase 1: Foundation
✅ complete. 

### Phase 2: Content Collection
✅ Complete
- ✅ Installed feedparser package
- ✅ Implemented YouTube RSS feed parser ([youtube_scraper.py](app/scrapers/youtube_scraper.py))
- ✅ Created helper script to get channel IDs from @handles ([get_channel_id.py](app/scrapers/get_channel_id.py))
- ✅ Tested successfully with @indydevdan channel
- Features:
  - Fetch latest videos via RSS feeds
  - Extract video metadata (title, description, published date, video ID)
  - Support for up to 15 videos per channel (RSS limit) 

### Phase 2.1: Content Collection - Anthropic Blog Scraper
✅ Complete
- ✅ Implemented Anthropic blog scraper ([anthropic_scraper.py](app/scrapers/anthropic_scraper.py))
- ✅ Created comprehensive test script ([test_anthropic_scraper.py](test_anthropic_scraper.py))
- ✅ Added to package exports for clean imports
- Features:
  - Scrape articles from Anthropic Research blog (https://www.anthropic.com/research)
  - Scrape articles from Anthropic Engineering blog (https://www.anthropic.com/engineering)
  - Extract article metadata: title, slug, URL, published date, summary, subject tags
  - BeautifulSoup-based HTML parsing with robust error handling
  - Support for pages with and without date information
  - Duplicate prevention using URL tracking

### Phase 2.2: Content Collection - Additional Blog Sources
- Build scrapers for other blog sources (OpenAI, Google AI, etc.)

### Phase 3: AI Processing
- Integrate LLM for content summarization
- Implement agent system prompt configuration
- Build daily digest generator

### Phase 4: Delivery & Deployment
- Implement email service
- Set up Render deployment
- Configure 24-hour scheduling
- Testing and optimization

---

## Key Requirements

- ✅ Easy deployment to Render
- ✅ Minimal Docker setup for local development
- ✅ Scalable architecture for adding new sources
- ✅ Configurable user insights for personalized summaries
- ✅ Reliable 24-hour scheduling

---

## Getting Started

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- PostgreSQL (via Docker)

### Installation

1. Clone the repository
2. Set up environment variables (see `.env.example`)
3. Run Docker containers
4. Initialize database
5. Start the application

### Configuration

Configure your content sources and user insights in the application settings.

### Testing Scrapers

**Test YouTube Scraper:**
```bash
python test_youtube_scraper.py
```

**Test Anthropic Blog Scraper:**
```bash
python test_anthropic_scraper.py
```

**Test Individual Methods:**
```python
# In Python shell
from app.scrapers import YouTubeScraper, AnthropicScraper

# Test YouTube scraper
videos = YouTubeScraper.fetch_videos("CHANNEL_ID", max_results=5)

# Test Anthropic scraper
research_articles = AnthropicScraper.fetch_research_articles(5)
engineering_articles = AnthropicScraper.fetch_engineering_articles(5)
all_articles = AnthropicScraper.fetch_all_articles(10)
```
