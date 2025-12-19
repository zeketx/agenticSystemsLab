"""Test script for YouTube scraper."""

from app.scrapers.youtube_scraper import YouTubeScraper

INDYDEVDAN_CHANNEL_ID = "UC_x36zCEGilGpB1m-V4gmjg"

def test_scraper():
    """Test the YouTube scraper."""
    print("Testing YouTube RSS Feed Scraper")
    print("=" * 50)

    try:
        videos = YouTubeScraper.fetch_videos(INDYDEVDAN_CHANNEL_ID, max_results=5)

        print(f"\nFound {len(videos)} videos from @indydevdan:\n")

        for i, video in enumerate(videos, 1):
            print(f"{i}. {video.title}")
            print(f"   Channel: {video.channel_name}")
            print(f"   Published: {video.published_date}")
            print(f"   Link: {video.link}")
            print(f"   Video ID: {video.video_id}")
            if video.description:
                print(f"   Description: {video.description[:100]}...")
            print()

        # Test Pydantic validation
        print("\n" + "=" * 50)
        print("Testing Pydantic Validation")
        print("=" * 50 + "\n")

        if videos:
            first_video = videos[0]

            # Test valid data access
            print("Model serialization:")
            print(f"  Model dict keys: {list(first_video.model_dump().keys())}")
            print(f"  JSON output (first 200 chars): {first_video.model_dump_json(indent=2)[:200]}...\n")

            # Test validation - try to create invalid VideoData
            from app.scrapers.youtube_scraper import VideoData

            print("Testing invalid video_id (should fail):")
            try:
                invalid = VideoData(
                    title="Test",
                    video_id="INVALID",  # Wrong format - needs 11 chars
                    channel_name="Test Channel",
                    channel_id="UC1234567890123456789012",
                    published_date=first_video.published_date,
                    link="https://youtube.com/watch?v=test",
                    description="Test"
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

            print("Testing invalid channel_id (should fail):")
            try:
                invalid = VideoData(
                    title="Test",
                    video_id="kFpLzCVLA20",
                    channel_name="Test Channel",
                    channel_id="INVALID_ID",  # Wrong format - needs UC prefix + 22 chars
                    published_date=first_video.published_date,
                    link="https://youtube.com/watch?v=test",
                    description="Test"
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

            print("Testing invalid URL domain (should fail):")
            try:
                invalid = VideoData(
                    title="Test",
                    video_id="kFpLzCVLA20",
                    channel_name="Test Channel",
                    channel_id="UC1234567890123456789012",
                    published_date=first_video.published_date,
                    link="https://vimeo.com/watch?v=test",  # Wrong domain
                    description="Test"
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scraper()
