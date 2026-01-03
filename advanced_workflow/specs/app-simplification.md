# App Simplification Plan

## Summary
Strip bloat from the app, integrate transcripts properly, and add an entry point for 24-hour automated runs.

---

## Changes Overview

| Action | Target | Reason |
|--------|--------|--------|
| DELETE | `app/agent/` | Empty placeholder (1 line) |
| MOVE | `TranscriptData` model | From `youtube_transcript.py` to `app/models/transcript.py` |
| MODIFY | `VideoData` | Add optional `transcript` field |
| MODIFY | `orchestrator.py` | Integrate transcript fetching |
| CREATE | `app/__main__.py` | Entry point for `python -m app` |

---

## Implementation Steps

### Step 1: Remove Empty Agent Directory
```
DELETE: app/agent/__init__.py
DELETE: app/agent/
```

### Step 2: Create Transcript Model
**New file: `app/models/transcript.py`**

Extract `TranscriptData` class from `youtube_transcript.py` into its own module.

**Update `app/models/__init__.py`:**
```python
from app.models.transcript import TranscriptData
# Add TranscriptData to __all__
```

### Step 3: Update youtube_transcript.py
- Remove `TranscriptData` class definition
- Import from: `from app.models import TranscriptData`
- Keep `get_transcript()` function as-is

### Step 4: Add Transcript Field to VideoData
**File: `app/scrapers/youtube_scraper.py`**

```python
from app.models import TranscriptData

class VideoData(BaseModel):
    # ... existing fields ...
    transcript: Optional[TranscriptData] = Field(default=None)
```

### Step 5: Integrate Transcripts into Orchestrator
**File: `app/services/orchestrator.py`**

1. Add parameter:
```python
def aggregate_content(
    config_path: Optional[str] = None,
    include_youtube: bool = True,
    include_blogs: bool = True,
    include_transcripts: bool = True  # NEW
) -> AggregatedContent:
```

2. In `_fetch_youtube_videos()`, after fetching videos:
```python
if fetch_transcripts:
    for video in videos:
        try:
            video.transcript = get_transcript(video.video_id)
        except Exception as e:
            logger.warning(f"Transcript failed for {video.video_id}: {e}")
```

### Step 6: Create Entry Point
**New file: `app/__main__.py`**

```python
"""Entry point: python -m app"""

import argparse
import logging
import sys
from pathlib import Path
from app.services import ContentAggregator

def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate content from sources")
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--no-youtube", action="store_true")
    parser.add_argument("--no-blogs", action="store_true")
    parser.add_argument("--no-transcripts", action="store_true")
    parser.add_argument("--quiet", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        result = ContentAggregator.aggregate_content(
            config_path=args.config,
            include_youtube=not args.no_youtube,
            include_blogs=not args.no_blogs,
            include_transcripts=not args.no_transcripts,
        )

        json_output = result.model_dump_json(indent=2)

        if args.output:
            Path(args.output).write_text(json_output)
        else:
            print(json_output)

        return 1 if result.metadata.has_errors else 0

    except Exception as e:
        logging.error(f"Aggregation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### Step 7: Update Exports
**File: `app/services/__init__.py`**
```python
from app.services.orchestrator import ContentAggregator
from app.services.youtube_transcript import get_transcript
from app.models import TranscriptData

__all__ = ['ContentAggregator', 'get_transcript', 'TranscriptData']
```

---

## Execution Order
1. Step 2 - Create `app/models/transcript.py`
2. Step 3 - Update `youtube_transcript.py` imports
3. Step 4 - Add transcript field to `VideoData`
4. Step 5 - Integrate into orchestrator
5. Step 7 - Update exports
6. Step 6 - Create `__main__.py`
7. Step 1 - Delete `app/agent/`

---

## Usage After Implementation

```bash
# Full aggregation
python -m app

# Save to file (for cron)
python -m app --output /path/to/results.json

# Quick run without transcripts
python -m app --no-transcripts

# Quiet mode for cron
python -m app --quiet --output results.json
```

---

## Files Modified/Created

| File | Action |
|------|--------|
| `app/agent/__init__.py` | DELETE |
| `app/models/transcript.py` | CREATE |
| `app/models/__init__.py` | MODIFY |
| `app/services/youtube_transcript.py` | MODIFY |
| `app/scrapers/youtube_scraper.py` | MODIFY |
| `app/services/orchestrator.py` | MODIFY |
| `app/services/__init__.py` | MODIFY |
| `app/__main__.py` | CREATE |
