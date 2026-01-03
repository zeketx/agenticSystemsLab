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

## Step 3: Minimal Code

**app/db.py** (single file, ~60 lines):
```python
import os
from sqlalchemy import create_engine, text
from app.scrapers import VideoData, ArticleData

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://newsagg:newsagg@localhost/newsagg")
engine = create_engine(DATABASE_URL)

def save_video(video: VideoData):
    """Upsert video - skip if exists"""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO videos (video_id, title, channel_name, channel_id, published_at, link, description, transcript_text)
            VALUES (:video_id, :title, :channel_name, :channel_id, :published_at, :link, :description, :transcript_text)
            ON CONFLICT (video_id) DO NOTHING
        """), video.model_dump())
        conn.commit()

def save_article(article: ArticleData):
    """Upsert article - skip if exists"""
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO articles (url, title, slug, published_at, summary, subjects)
            VALUES (:url, :title, :slug, :published_at, :summary, :subjects)
            ON CONFLICT (url) DO NOTHING
        """), article.model_dump())
        conn.commit()

def save_all(videos: list, articles: list) -> dict:
    """Save all content, return stats"""
    v_count = sum(1 for v in videos if save_video(v))
    a_count = sum(1 for a in articles if save_article(a))
    return {"videos_saved": v_count, "articles_saved": a_count}
```

---

## Step 4: CLI Flag

**Add to app/__main__.py:**
```python
parser.add_argument("--save-to-db", action="store_true", help="Save results to database")

# After aggregation:
if args.save_to_db:
    from app.db import save_all
    stats = save_all(result.videos, result.articles)
    logging.info(f"Saved to DB: {stats}")
```

---

## Files

| File | Action | Lines |
|------|--------|-------|
| `docker-compose.yml` | MOVE to root | ~15 |
| `app/db.py` | CREATE | ~60 |
| `app/__main__.py` | ADD flag | +10 |

**Total new code: ~70 lines**

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
