-- Database migration for content enrichment tracking
-- Run this on existing databases to add enrichment support

-- Videos: Add enrichment tracking columns
ALTER TABLE videos
    ADD COLUMN IF NOT EXISTS transcript_enriched_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS transcript_fetch_attempted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS transcript_fetch_error TEXT;

-- Articles: Add full content storage and enrichment tracking columns
ALTER TABLE articles
    ADD COLUMN IF NOT EXISTS content_markdown TEXT,
    ADD COLUMN IF NOT EXISTS content_enriched_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS content_fetch_attempted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS content_fetch_error TEXT;

-- Create indexes for efficient querying of unenriched content
CREATE INDEX IF NOT EXISTS idx_videos_transcript_null
    ON videos(id) WHERE transcript_text IS NULL AND transcript_fetch_attempted = FALSE;

CREATE INDEX IF NOT EXISTS idx_articles_content_null
    ON articles(id) WHERE content_markdown IS NULL AND content_fetch_attempted = FALSE;

-- Create indexes for enrichment timestamp queries
CREATE INDEX IF NOT EXISTS idx_videos_enriched_at ON videos(transcript_enriched_at);
CREATE INDEX IF NOT EXISTS idx_articles_enriched_at ON articles(content_enriched_at);

-- Display migration summary
DO $$
BEGIN
    RAISE NOTICE 'Enrichment migration completed successfully';
    RAISE NOTICE 'Added columns to videos table: transcript_enriched_at, transcript_fetch_attempted, transcript_fetch_error';
    RAISE NOTICE 'Added columns to articles table: content_markdown, content_enriched_at, content_fetch_attempted, content_fetch_error';
    RAISE NOTICE 'Created indexes for efficient enrichment queries';
END $$;
