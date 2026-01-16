-- Initialize database schema for news aggregator

-- Videos table (YouTube content)
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(11) UNIQUE NOT NULL,  -- dedup key
    title TEXT NOT NULL,
    channel_name VARCHAR(200),
    channel_id VARCHAR(24),
    published_at TIMESTAMP,
    link TEXT,
    description TEXT,
    transcript_text TEXT,
    transcript_enriched_at TIMESTAMP,
    transcript_fetch_attempted BOOLEAN DEFAULT FALSE,
    transcript_fetch_error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Articles table (Blog content)
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,  -- dedup key
    title TEXT NOT NULL,
    slug VARCHAR(255),
    published_at TIMESTAMP,
    summary TEXT,
    subjects TEXT[],
    content_markdown TEXT,
    content_enriched_at TIMESTAMP,
    content_fetch_attempted BOOLEAN DEFAULT FALSE,
    content_fetch_error TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);

-- Create indexes for enrichment queries
CREATE INDEX IF NOT EXISTS idx_videos_transcript_null
    ON videos(id) WHERE transcript_text IS NULL AND transcript_fetch_attempted = FALSE;
CREATE INDEX IF NOT EXISTS idx_articles_content_null
    ON articles(id) WHERE content_markdown IS NULL AND content_fetch_attempted = FALSE;
CREATE INDEX IF NOT EXISTS idx_videos_enriched_at ON videos(transcript_enriched_at);
CREATE INDEX IF NOT EXISTS idx_articles_enriched_at ON articles(content_enriched_at);
