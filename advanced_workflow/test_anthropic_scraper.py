"""Test script for Anthropic blog scraper."""

from app.scrapers.anthropic_scraper import AnthropicScraper


def test_research_articles():
    """Test fetching research articles."""
    print("Testing Anthropic Research Blog Scraper")
    print("=" * 50)

    try:
        articles = AnthropicScraper.fetch_research_articles(max_results=5)

        print(f"\nFound {len(articles)} research articles:\n")

        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source_type}")
            print(f"   Published: {article.published_date}")
            print(f"   URL: {article.url}")
            print(f"   Slug: {article.slug}")
            if article.summary:
                print(f"   Summary: {article.summary[:100]}...")
            if article.subjects:
                print(f"   Tags: {', '.join(article.subjects)}")
            print()

    except Exception as e:
        print(f"Error: {e}")


def test_engineering_articles():
    """Test fetching engineering articles."""
    print("\nTesting Anthropic Engineering Blog Scraper")
    print("=" * 50)

    try:
        articles = AnthropicScraper.fetch_engineering_articles(max_results=5)

        print(f"\nFound {len(articles)} engineering articles:\n")

        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source_type}")
            print(f"   Published: {article.published_date}")
            print(f"   URL: {article.url}")
            print(f"   Slug: {article.slug}")
            if article.summary:
                print(f"   Summary: {article.summary[:100]}...")
            if article.subjects:
                print(f"   Tags: {', '.join(article.subjects)}")
            print()

    except Exception as e:
        print(f"Error: {e}")


def test_all_articles():
    """Test fetching all articles from both sources."""
    print("\nTesting Combined Anthropic Blog Scraper")
    print("=" * 50)

    try:
        articles = AnthropicScraper.fetch_all_articles(max_results=3)

        print(f"\nFound {len(articles)} total articles (sorted by date):\n")

        for i, article in enumerate(articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Source: {article.source_type}")
            print(f"   Published: {article.published_date}")
            print(f"   URL: {article.url}")
            print()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_research_articles()
    test_engineering_articles()
    test_all_articles()
