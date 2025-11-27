"""Test script for YouTube transcript service."""

from app.services.youtube_transcript import get_transcript

def test_transcript():
    """Test the transcript fetching service."""
    print("Testing YouTube Transcript Service")
    print("=" * 50)

    test_video_id = "kFpLzCVLA20"
    print(f"\nFetching transcript for video ID: {test_video_id}\n")

    try:
        transcript = get_transcript(test_video_id)

        print(f"Transcript length: {len(transcript)} characters")
        print(f"\nFirst 500 characters:\n{transcript[:500]}...")
        print(f"\n...Last 500 characters:\n...{transcript[-500:]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_transcript()
