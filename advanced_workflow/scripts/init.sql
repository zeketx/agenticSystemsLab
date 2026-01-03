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
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id);
