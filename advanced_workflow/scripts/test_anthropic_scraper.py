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

        # Test Pydantic validation
        print("\n" + "=" * 50)
        print("Testing Pydantic Validation")
        print("=" * 50 + "\n")

        if articles:
            first_article = articles[0]

            # Test valid data access
            print("Model serialization:")
            print(f"  Model dict keys: {list(first_article.model_dump().keys())}")
            print(f"  JSON output (first 200 chars): {first_article.model_dump_json(indent=2)[:200]}...\n")

            # Test validation - try invalid source_type
            from app.scrapers.anthropic_scraper import ArticleData

            print("Testing invalid source_type (should fail):")
            try:
                invalid = ArticleData(
                    title="Test Article",
                    slug="test-article",
                    url="https://www.anthropic.com/test",
                    published_date=first_article.published_date,
                    summary="Test summary",
                    subjects=["test"],
                    source_type="invalid_type"  # Invalid literal - must be 'research' or 'engineering'
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

            print("Testing invalid URL domain (should fail):")
            try:
                invalid = ArticleData(
                    title="Test Article",
                    slug="test-article",
                    url="https://www.google.com/test",  # Wrong domain - must be anthropic.com
                    published_date=first_article.published_date,
                    summary="Test summary",
                    subjects=["test"],
                    source_type="research"
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}\n")

            print("Testing invalid slug pattern (should fail):")
            try:
                invalid = ArticleData(
                    title="Test Article",
                    slug="invalid slug with spaces!",  # Invalid - must be alphanumeric with hyphens/underscores
                    url="https://www.anthropic.com/test",
                    published_date=first_article.published_date,
                    summary="Test summary",
                    subjects=["test"],
                    source_type="research"
                )
                print("  ✗ Validation did NOT fail (unexpected)")
            except Exception as e:
                print(f"  ✓ Validation correctly failed: {str(e)[:100]}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_research_articles()
    test_engineering_articles()
    test_all_articles()
