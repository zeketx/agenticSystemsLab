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

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scraper()
