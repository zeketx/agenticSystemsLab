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
- **Language:** Python
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy for database models and table creation

### Project Structure
```
project-root/
├── app/              # All application logic
│   ├── agents/       # SQLAlchemy models
│   ├── services/     # Business logic (scraping, LLM, email)
│   └── scrapers/
└── docker/           # Docker configuration
    └── postgres/     # Minimal PostgreSQL setup
```

### Infrastructure
- **Containerization:** Docker setup for PostgreSQL
- **Deployment:** Render platform
- **Scheduling:** 24-hour cron/scheduled jobs on Render

---

## Development Phases

### Phase 1: Foundation
- Set up a pyproject.toml file with the following dependences.
[project]
name = "ai-news-aggregator"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "beautifulsoup4>=4.14.2",
    "docling>=2.61.2",
    "feedparser>=6.0.12",
    "markdown>=3.7.0",
    "markdownify>=0.11.6",
    "openai>=2.7.2",
    "psycopg2-binary>=2.9.11",
    "pydantic>=2.0.0",
    "python-dotenv>=1.2.1",
    "requests>=2.32.5",
    "sqlalchemy>=2.0.44",
    "youtube-transcript-api>=1.2.3",
]

[dependency-groups]
dev = [
    "ipykernel>=7.1.0",
]
- Configure docker-compose.yml

### Phase 2: Content Collection
- Install packages needed for video scaper and YouTubeTranscriptAPI 
- Implement YouTube RSS feed parser
- 

### Phase 2.1: Content Collection
- Build blog post scraper

### Phase 2.2: Content Collection
- Build blog post scraper

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
