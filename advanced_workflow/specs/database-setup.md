# Minimal Database Setup

## Goal
Get scraper output into PostgreSQL with deduplication. No extras.

---

## What We're Building

```
python -m app → JSON → Database (with dedup)
```

---

## Step 1: Docker (PostgreSQL only)

**Move & simplify docker-compose.yml:**
```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: news-aggregator-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-newsagg}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-newsagg}
      POSTGRES_DB: ${POSTGRES_DB:-newsagg}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

**Commands:**
```bash
cp .env.example .env
docker-compose up -d
```

---

## Step 2: Two Tables (match existing Pydantic models)

**videos table:**
```sql
CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(11) UNIQUE NOT NULL,  -- dedup key
    title TEXT NOT NULL,
    channel_name VARCHAR(200),
    channel_id VARCHAR(24),
    published_at TIMESTAMP,
    link TEXT,
    description TEXT,
    transcript_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**articles table:**
```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,  -- dedup key
    title TEXT NOT NULL,
    slug VARCHAR(255),
    published_at TIMESTAMP,
    summary TEXT,
    subjects TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Step 3: Database Module

**app/database/** (structured folder):

```
app/database/
├── __init__.py       # Exports
├── connections.py    # Engine setup
├── createTables.py   # Schema initialization
├── models.py         # Table definitions
└── repository.py     # Save operations
```

**connections.py**:
```python
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://newsagg:newsagg@localhost:5432/newsagg")
engine = create_engine(DATABASE_URL)
```

**createTables.py**:
```python
from pathlib import Path
from app.database.connections import engine

def create_tables():
    """Execute init.sql to create tables"""
    sql = Path("scripts/init.sql").read_text()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
```

**models.py**:
```python
from sqlalchemy import Table, Column, Integer, String, Text, TIMESTAMP, ARRAY, MetaData

metadata = MetaData()

videos = Table('videos', metadata,
    Column('id', Integer, primary_key=True),
    Column('video_id', String(11), unique=True, nullable=False),
    Column('title', Text, nullable=False),
    Column('channel_name', String(200)),
    Column('channel_id', String(24)),
    Column('published_at', TIMESTAMP),
    Column('link', Text),
    Column('description', Text),
    Column('transcript_text', Text),
    Column('created_at', TIMESTAMP, server_default='NOW()')
)

articles = Table('articles', metadata,
    Column('id', Integer, primary_key=True),
    Column('url', Text, unique=True, nullable=False),
    Column('title', Text, nullable=False),
    Column('slug', String(255)),
    Column('published_at', TIMESTAMP),
    Column('summary', Text),
    Column('subjects', ARRAY(Text)),
    Column('created_at', TIMESTAMP, server_default='NOW()')
)
```

**repository.py**:
```python
import logging
from sqlalchemy import text
from app.scrapers import VideoData, ArticleData
from app.database.connections import engine

logger = logging.getLogger(__name__)

def save_video(video: VideoData) -> bool:
    """Upsert video - skip if exists"""
    # [implementation from current app/db.py]

def save_article(article: ArticleData) -> bool:
    """Upsert article - skip if exists"""
    # [implementation from current app/db.py]

def save_all(videos: list, articles: list) -> dict:
    """Save all content, return stats"""
    # [implementation from current app/db.py]
```

**__init__.py**:
```python
from app.database.repository import save_video, save_article, save_all

__all__ = ['save_video', 'save_article', 'save_all']
```

---

## Step 4: CLI Flag

**Add to app/__main__.py:**
```python
parser.add_argument("--save-to-db", action="store_true", help="Save results to database")

# After aggregation:
if args.save_to_db:
    from app.database.repository import save_all
    stats = save_all(result.videos, result.articles)
    logging.info(f"Saved to DB: {stats}")
```

---

## Files

| File | Action | Lines |
|------|--------|-------|
| `docker-compose.yml` | EXISTS at root | ~22 |
| `scripts/init.sql` | EXISTS | ~33 |
| `app/database/__init__.py` | CREATE | ~4 |
| `app/database/connections.py` | CREATE | ~5 |
| `app/database/createTables.py` | CREATE | ~10 |
| `app/database/models.py` | CREATE | ~25 |
| `app/database/repository.py` | CREATE | ~140 |
| `app/__main__.py` | UPDATE import | 1 line |

**Total: ~185 lines (refactored from app/db.py)**

---

## Usage

```bash
# Start database
docker-compose up -d

# Run aggregation and save to DB
python -m app --no-transcripts --save-to-db

# Run again - duplicates skipped automatically
python -m app --no-transcripts --save-to-db
```

---

## Dedup Strategy

- **Videos:** `ON CONFLICT (video_id) DO NOTHING`
- **Articles:** `ON CONFLICT (url) DO NOTHING`

Same content = same key = skipped. Simple.
