"""Test script for YouTube transcript service with Pydantic model."""

from app.services.youtube_transcript import get_transcript, TranscriptData


def test_transcript():
    """Test the transcript fetching service with Pydantic model."""
    print("Testing YouTube Transcript Service")
    print("=" * 50)

    test_video_id = "kFpLzCVLA20"
    print(f"\nFetching transcript for video ID: {test_video_id}\n")

    try:
        # Test with TranscriptData model (new default behavior)
        transcript_data = get_transcript(test_video_id, return_model=True)

        print(f"Transcript available: {transcript_data.is_available}")
        print(f"Video ID: {transcript_data.video_id}")
        print(f"Character count: {transcript_data.char_count:,}")
        print(f"Word count: {transcript_data.word_count:,}")
        print(f"Fetched at: {transcript_data.fetched_at}")

        if transcript_data.is_available:
            print(f"\nFirst 500 characters:\n{transcript_data.transcript_text[:500]}...")
            print(f"\n...Last 500 characters:\n...{transcript_data.transcript_text[-500:]}")
        else:
            print(f"\nError: {transcript_data.error_message}")

        # Test model serialization
        print("\n" + "=" * 50)
        print("Model Serialization Tests")
        print("=" * 50 + "\n")

        print("Model dict:")
        model_dict = transcript_data.model_dump()
        print(f"  - video_id: {model_dict['video_id']}")
        print(f"  - is_available: {model_dict['is_available']}")
        print(f"  - char_count: {model_dict['char_count']}")
        print(f"  - word_count: {model_dict['word_count']}")

        print("\nModel JSON (first 300 chars):")
        json_output = transcript_data.model_dump_json(indent=2)
        print(json_output[:300] + "...")

        # Test backward compatibility with string return
        print("\n" + "=" * 50)
        print("Backward Compatibility Test (return_model=False)")
        print("=" * 50 + "\n")

        transcript_string = get_transcript(test_video_id, return_model=False)
        print(f"Type: {type(transcript_string)}")
        print(f"Length: {len(transcript_string):,} characters")
        print(f"First 200 chars: {transcript_string[:200]}...")

        # Test validation
        print("\n" + "=" * 50)
        print("Validation Tests")
        print("=" * 50 + "\n")

        print("Testing invalid video_id (should fail):")
        try:
            invalid = TranscriptData(
                video_id="INVALID",  # Wrong format - needs 11 chars
                transcript_text="Test transcript",
                char_count=100,
                word_count=20
            )
            print("  ✗ Validation did NOT fail (unexpected)")
        except Exception as e:
            print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

        print("Testing empty transcript_text (should fail):")
        try:
            invalid = TranscriptData(
                video_id="kFpLzCVLA20",
                transcript_text="",  # Empty text
                char_count=0,
                word_count=0
            )
            print("  ✗ Validation did NOT fail (unexpected)")
        except Exception as e:
            print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

        print("Testing whitespace-only transcript_text (should fail):")
        try:
            invalid = TranscriptData(
                video_id="kFpLzCVLA20",
                transcript_text="   ",  # Whitespace only
                char_count=0,
                word_count=0
            )
            print("  ✗ Validation did NOT fail (unexpected)")
        except Exception as e:
            print(f"  ✓ Validation correctly failed: {str(e)[:100]}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_transcript()
