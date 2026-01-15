# YouTube Transcript Service

## Problem Statement

**Issue**: After implementing database storage for videos and articles, we discovered that `transcript_text` was always NULL in the database, even though the app has a working transcript fetching service at `app/services/youtube_transcript.py` with a test script at `scripts/test_transcript.py`.

**Goal**: Understand why transcripts aren't being saved to the database and document the expected behavior for future developers.

**Root Cause**: YouTube is blocking transcript API requests from cloud/server IPs. When transcripts fail to fetch, the `TranscriptData` model returns `is_available=False`, and the repository code (app/database/repository.py:25) only saves transcript_text when `is_available=True`. Therefore, NULL in the database is the **correct behavior** when transcripts are unavailable.

**Resolution**: This is working as designed. The system gracefully handles unavailable transcripts by storing NULL instead of error messages. To test the service, run the test script locally (non-cloud IP) with `python scripts/test_transcript.py`.

## Overview
The YouTube Transcript Service fetches and processes video transcripts from YouTube using the `youtube-transcript-api` library. It provides validated Pydantic models for type-safe transcript handling.

## Architecture

### Components
1. **Service Layer**: `app/services/youtube_transcript.py`
2. **Model Layer**: `app/models/transcript.py`
3. **Test Script**: `scripts/test_transcript.py`

### Data Flow
```
YouTube Video ID → get_transcript() → YouTube API → TranscriptData Model → Database/JSON
```

## Core Model: TranscriptData

### Fields
```python
video_id: str           # 11-character YouTube video ID (validated)
transcript_text: str    # Full transcript text (min 1 char)
fetched_at: datetime    # Timestamp of fetch
char_count: int         # Character count (≥0)
word_count: int         # Word count (≥0)
is_available: bool      # True if transcript successfully fetched
error_message: str?     # Error details if unavailable (optional)
```

### Validation Rules
- **video_id**: Must match pattern `^[a-zA-Z0-9_-]{11}$`
- **transcript_text**: Cannot be empty or whitespace-only
- **char_count/word_count**: Must be ≥0
- Whitespace is automatically stripped from string fields

## Service API

### Function: `get_transcript(video_id, return_model=True)`

#### Parameters
- `video_id` (str): 11-character YouTube video ID
- `return_model` (bool): Returns TranscriptData if True, plain string if False

#### Returns
- **Success**: TranscriptData with `is_available=True` and full transcript
- **Failure**: TranscriptData with `is_available=False` and error message

#### Example Usage
```python
from app.services.youtube_transcript import get_transcript

# Fetch transcript as Pydantic model
transcript = get_transcript("kFpLzCVLA20")

if transcript.is_available:
    print(f"Got {transcript.word_count} words")
    print(transcript.transcript_text[:500])
else:
    print(f"Error: {transcript.error_message}")

# Backward compatible string mode
text = get_transcript("kFpLzCVLA20", return_model=False)
```

## Error Handling

### Common Errors
1. **TranscriptsDisabled**: Video has transcripts disabled
2. **NoTranscriptFound**: No transcript available in any language
3. **VideoUnavailable**: Video doesn't exist or is private
4. **IP Blocked**: YouTube blocking requests from your IP

### IP Blocking
YouTube may block requests from:
- Cloud providers (AWS, GCP, Azure, etc.)
- IPs making too many requests

**Solution**: See [youtube-transcript-api README](https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans)

## Database Integration

### Storage Strategy
```python
# In app/database/repository.py
transcript_text = None
if video.transcript and video.transcript.is_available:
    transcript_text = video.transcript.transcript_text
# Saves NULL if unavailable
```

### Database Schema
```sql
CREATE TABLE videos (
    ...
    transcript_text TEXT,  -- NULL if unavailable
    ...
);
```

## Testing

### Run Test Script
```bash
python scripts/test_transcript.py
```

### Test Coverage
1. ✅ Fetches real transcript from YouTube
2. ✅ Handles unavailable transcripts gracefully
3. ✅ Validates Pydantic model fields
4. ✅ Tests backward compatibility (string mode)
5. ✅ Validates video_id format
6. ✅ Rejects empty/whitespace transcript_text

### Expected Output
```
Testing YouTube Transcript Service
==================================================

Fetching transcript for video ID: kFpLzCVLA20

Transcript available: True/False
Video ID: kFpLzCVLA20
Character count: X,XXX
Word count: X,XXX
Fetched at: YYYY-MM-DD HH:MM:SS

First 500 characters:
[Transcript preview...]
```

## Integration with Aggregation System

### In `app/scrapers/youtube_scraper.py`
```python
from app.services.youtube_transcript import get_transcript

# Fetch transcript for each video
transcript = get_transcript(video_id)
video_data = VideoData(
    video_id=video_id,
    title=title,
    transcript=transcript,  # TranscriptData model
    ...
)
```

### CLI Flags
- `python -m app` - Fetches transcripts (slow: ~18s)
- `python -m app --no-transcripts` - Skips transcripts (fast: ~1s)

## Performance Characteristics

| Mode | Duration | Use Case |
|------|----------|----------|
| With transcripts | ~18s | Full content analysis |
| Without transcripts | ~1s | Quick metadata aggregation |

**Rate limiting**: ~1 video/second to avoid IP bans

## Troubleshooting

### Problem: All transcripts show "No transcript available"
**Causes**:
1. IP blocked by YouTube (most common)
2. Transcripts actually disabled on videos
3. Network connectivity issues

**Diagnosis**:
```bash
# Test single video
python scripts/test_transcript.py

# Check error message in output
# If error mentions IP blocking, see workarounds below
```

**Solutions**:
1. Use residential IP (not cloud provider)
2. Add delays between requests
3. Use proxy/VPN
4. See [API documentation](https://github.com/jdepoix/youtube-transcript-api)

### Problem: Validation errors when creating TranscriptData
**Cause**: Invalid field values

**Solution**: Check validation rules
```python
# ✗ Invalid - empty text
TranscriptData(
    video_id="abc",  # ✗ Wrong format (needs 11 chars)
    transcript_text="",  # ✗ Empty
    ...
)

# ✓ Valid
TranscriptData(
    video_id="kFpLzCVLA20",  # ✓ 11 chars
    transcript_text="Transcript content here",  # ✓ Non-empty
    char_count=100,
    word_count=20
)
```

## Future Enhancements

### Potential Improvements
1. **Multi-language support**: Fetch transcripts in preferred language
2. **Caching**: Cache transcripts to avoid re-fetching
3. **Retry logic**: Automatic retry with exponential backoff
4. **Proxy rotation**: Rotate IPs to avoid blocking
5. **Progress tracking**: Show progress when fetching many transcripts

### Database Optimizations
1. **Full-text search**: Add GIN index on transcript_text
2. **Compression**: Compress transcript_text to save space
3. **Separate table**: Move transcripts to dedicated table

## Dependencies

```toml
[project]
dependencies = [
    "youtube-transcript-api>=0.6.0",
    "pydantic>=2.0.0",
]
```

## References

- [youtube-transcript-api GitHub](https://github.com/jdepoix/youtube-transcript-api)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [YouTube Data API](https://developers.google.com/youtube/v3)

## Support

For issues related to:
- **Transcript fetching**: See youtube-transcript-api issues
- **Model validation**: Check Pydantic docs
- **Database storage**: See app/database/repository.py
- **Integration**: See app/scrapers/youtube_scraper.py
