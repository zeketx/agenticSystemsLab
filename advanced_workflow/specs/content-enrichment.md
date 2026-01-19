# Content Enrichment Pipeline

**Status:** ✅ Implemented
**Date:** January 2026
**Purpose:** Backfill missing transcripts and article content for database entries

## Overview

Stage 2 of the content aggregation system focuses on enriching database entries with full content that may not have been captured during initial aggregation:

1. **Video Transcripts**: Fetch transcripts for videos that were saved without transcript_text
2. **Article Content**: Extract full article body as markdown from article URLs

## Architecture

### Database Schema Extensions

#### Videos Table Additions
```sql
ALTER TABLE videos
    ADD COLUMN transcript_enriched_at TIMESTAMP,
    ADD COLUMN transcript_fetch_attempted BOOLEAN DEFAULT FALSE,
    ADD COLUMN transcript_fetch_error TEXT;
```

#### Articles Table Additions
```sql
ALTER TABLE articles
    ADD COLUMN content_markdown TEXT,
    ADD COLUMN content_enriched_at TIMESTAMP,
    ADD COLUMN content_fetch_attempted BOOLEAN DEFAULT FALSE,
    ADD COLUMN content_fetch_error TEXT;
```

### Key Design Decisions

#### 1. Separate `content_markdown` Field
- **Decision**: Add new field instead of repurposing `summary`
- **Rationale**:
  - `summary` contains short excerpts (150-300 chars)
  - Full content is 10-50KB
  - Semantic separation allows different use cases
  - Backward compatible with existing aggregation

#### 2. Idempotency via `fetch_attempted` Flag
- **Decision**: Use boolean flag + separate error field
- **Rationale**:
  - Prevents infinite retries on permanent failures (deleted videos, paywalled content)
  - Distinguishes "not tried" from "tried and failed"
  - Allows manual retry by clearing flag
  - More robust than NULL checks

#### 3. Batch Processing
- **Decision**: Process items in configurable batches
- **Rationale**:
  - Better progress tracking
  - Natural resume points on interruption
  - Memory efficient
  - Easier rate limiting implementation

## Components

### 1. Database Repository (`app/database/enrichment_repository.py`)

**Functions**:
- `get_unenriched_videos(limit, offset)` - Query videos needing transcripts
- `get_unenriched_articles(limit, offset)` - Query articles needing content
- `update_video_transcript(video_id, text, success, error)` - Update video record
- `update_article_content(article_id, markdown, success, error)` - Update article record
- `get_enrichment_stats()` - Return enrichment statistics

**Pattern**: Follows existing `repository.py` using SQLAlchemy text() with transactions.

### 2. Article Content Fetcher (`app/services/article_content_fetcher.py`)

**Purpose**: Fetch full article HTML and convert to markdown

**Process**:
1. Fetch HTML with requests (timeout: 30s)
2. Parse with BeautifulSoup
3. Extract main content:
   - Try `<article>` tag first
   - Fallback to `<main>` tag
   - Remove noise (nav, footer, scripts, styles)
4. Convert to markdown using `markdownify` library
5. Clean up whitespace

**Dependencies**: requests, beautifulsoup4, markdownify

**Returns**: `Tuple[Optional[str], Optional[str]]` - (content, error_message)

### 3. Content Enrichment Orchestrator (`app/services/content_enrichment.py`)

**Functions**:
- `enrich_videos(batch_size, max_items, rate_limit)` - Backfill transcripts
- `enrich_articles(batch_size, max_items, rate_limit)` - Backfill content
- `enrich_all()` - Enrich both types

**Process**:
1. Query batch of unenriched items
2. For each item:
   - Call fetcher/transcript service
   - Update database with result
   - Log progress
   - Sleep for rate limiting
3. Continue until done or max_items reached

**Reuses**: `app/services/youtube_transcript.py:get_transcript()` for videos

### 4. CLI Command (`app/commands/enrich.py`)

**Flags**:
- `--stats` - Show enrichment statistics
- `--dry-run` - Preview what would be enriched
- `--videos-only` - Only enrich videos
- `--articles-only` - Only enrich articles
- `--limit N` - Maximum items to process
- `--batch-size N` - Items per batch (default: 50)
- `--rate-limit N` - Seconds between requests (default: 1.0)
- `--quiet` - Suppress progress output

**Examples**:
```bash
python -m app enrich --stats
python -m app enrich --dry-run
python -m app enrich --articles-only --limit 50
python -m app enrich --batch-size 25 --rate-limit 2.0
```

## Safety Features

### Idempotency
- Safe to run multiple times
- Already-enriched items are automatically skipped
- Automatic resume after interruption

### Error Handling
- Errors stored in database for analysis
- One failed item doesn't stop entire process
- Failed items can be manually retried by clearing `fetch_attempted` flag:
  ```sql
  UPDATE videos
  SET transcript_fetch_attempted = FALSE,
      transcript_fetch_error = NULL
  WHERE id = 123;
  ```

### Rate Limiting
- Configurable delays between requests
- Default: 0.5s for videos, 1.5s for articles
- Prevents overwhelming external servers
- Uses simple `time.sleep()` in enrichment loop

### Progress Tracking
- Log every batch completion
- Display statistics at end
- Real-time feedback during long-running operations

## Performance

### Database Indexes

Efficient queries via partial indexes:
```sql
-- Find unenriched videos
CREATE INDEX idx_videos_transcript_null
    ON videos(id)
    WHERE transcript_text IS NULL
      AND transcript_fetch_attempted = FALSE;

-- Find unenriched articles
CREATE INDEX idx_articles_content_null
    ON articles(id)
    WHERE content_markdown IS NULL
      AND content_fetch_attempted = FALSE;
```

### Network Performance
- Rate limiting prevents server overload
- Timeout on HTTP requests (30s) prevents hanging
- Batch processing allows progress tracking

### Memory Management
- Process items in batches, not all at once
- Don't hold large result sets in memory
- Clean up markdown to reduce storage size

## Migration

For existing databases:

```bash
# Copy migration file to container
docker cp scripts/enrichment_migration.sql news-aggregator-db:/tmp/

# Run migration
docker exec news-aggregator-db psql -U newsagg -d newsagg \
    -f /tmp/enrichment_migration.sql
```

## Testing

### Verification Queries

```sql
-- Check enrichment progress
SELECT
    COUNT(*) as total,
    COUNT(transcript_text) as with_transcript,
    COUNT(*) FILTER (WHERE transcript_text IS NULL) as without_transcript
FROM videos;

-- View enriched article content
SELECT id, title, LENGTH(content_markdown), content_enriched_at
FROM articles
WHERE content_markdown IS NOT NULL
LIMIT 10;

-- Check error cases
SELECT id, title, content_fetch_error
FROM articles
WHERE content_fetch_attempted = TRUE
  AND content_markdown IS NULL;
```

### Test Commands

```bash
# Dry run with small limit
python -m app enrich --dry-run --limit 5

# Test videos only
python -m app enrich --videos-only --limit 2

# Test articles only
python -m app enrich --articles-only --limit 2

# Verify idempotency (run twice)
python -m app enrich --limit 5
python -m app enrich --limit 5  # Should skip already-enriched items
```

## Future Enhancements

### Potential Improvements
1. **Parallel Processing**: Use multiprocessing for faster enrichment
2. **Retry Logic**: Exponential backoff for transient failures
3. **Content Quality Scoring**: Validate extracted content quality
4. **Incremental Enrichment**: Auto-enrich new items as they're added
5. **Content Caching**: Cache fetched HTML to avoid re-fetching on retry

### Stage 3 Integration
The enrichment pipeline prepares content for Stage 3 (LLM summarization):
- All video transcripts available in `transcript_text` field
- All article content available in `content_markdown` field
- Both are clean, markdown-formatted text ready for LLM processing

## Troubleshooting

### Failed Article Extraction

If articles fail with "Could not extract main content from page":

1. Inspect the article URL manually
2. Check HTML structure for `<article>` or `<main>` tags
3. Update `article_content_fetcher.py` extraction logic if needed
4. Clear error flag and retry:
   ```sql
   UPDATE articles
   SET content_fetch_attempted = FALSE,
       content_fetch_error = NULL
   WHERE url = 'https://example.com/article';
   ```

### Performance Issues

If enrichment is too slow:
- Increase `--batch-size` for fewer database round-trips
- Decrease `--rate-limit` if servers can handle faster requests
- Use `--videos-only` or `--articles-only` to focus on one type
- Run enrichment during off-peak hours

## Related Files

- `scripts/enrichment_migration.sql` - Database migration
- `scripts/init.sql` - Full schema with enrichment
- `app/database/models.py` - SQLAlchemy table definitions
- `app/__main__.py` - CLI entry point with subcommands
