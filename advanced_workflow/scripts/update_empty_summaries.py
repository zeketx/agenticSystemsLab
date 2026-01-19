"""Update empty article summaries by extracting from enriched content."""

import os
import sys
import re
from sqlalchemy import create_engine, text

# Create database engine directly
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://newsagg:newsagg@localhost:5432/newsagg"
)
engine = create_engine(DATABASE_URL)


def extract_summary_from_markdown(content_markdown: str, max_length: int = 300) -> str:
    """
    Extract a summary from markdown content.

    Takes the first substantial paragraph (>50 chars) from the content.

    Args:
        content_markdown: Full article content in markdown format
        max_length: Maximum length for summary

    Returns:
        Extracted summary text
    """
    if not content_markdown:
        return ""

    # Split by double newlines to get paragraphs
    paragraphs = content_markdown.split('\n\n')

    for para in paragraphs:
        # Clean up markdown formatting
        cleaned = para.strip()

        # Skip headers (lines starting with #)
        if cleaned.startswith('#'):
            continue

        # Skip image/link-only paragraphs
        if cleaned.startswith('![') or cleaned.startswith('[') and '](' in cleaned:
            continue

        # Remove markdown formatting for length check
        text_only = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)  # Remove links
        text_only = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text_only)  # Remove bold
        text_only = re.sub(r'\*([^\*]+)\*', r'\1', text_only)  # Remove italic
        text_only = re.sub(r'`([^`]+)`', r'\1', text_only)  # Remove code

        # Check if substantial
        if len(text_only.strip()) > 50:
            # Truncate to max_length if needed
            if len(text_only) > max_length:
                # Try to break at sentence end
                truncated = text_only[:max_length]
                last_period = truncated.rfind('.')
                last_question = truncated.rfind('?')
                last_exclaim = truncated.rfind('!')

                break_point = max(last_period, last_question, last_exclaim)
                if break_point > 100:  # Only break at sentence if reasonable position
                    return text_only[:break_point + 1].strip()
                else:
                    return truncated.strip() + "..."

            return text_only.strip()

    return ""


def update_empty_summaries():
    """Update articles with empty summaries using their enriched content."""
    try:
        with engine.connect() as conn:
            # Find articles with empty summaries but with enriched content
            result = conn.execute(text("""
                SELECT id, title, content_markdown
                FROM articles
                WHERE summary = ''
                  AND content_markdown IS NOT NULL
                  AND LENGTH(content_markdown) > 100
            """))

            articles = result.fetchall()
            print(f"Found {len(articles)} articles with empty summaries to update")

            updated_count = 0
            for article in articles:
                # Extract summary from content
                summary = extract_summary_from_markdown(article.content_markdown)

                if summary:
                    # Update the article
                    conn.execute(text("""
                        UPDATE articles
                        SET summary = :summary
                        WHERE id = :id
                    """), {"summary": summary, "id": article.id})

                    print(f"✓ Updated article {article.id}: {article.title[:50]}...")
                    updated_count += 1
                else:
                    print(f"✗ Could not extract summary for article {article.id}: {article.title[:50]}...")

            # Commit changes
            conn.commit()
            print(f"\n{'='*60}")
            print(f"Summary update complete!")
            print(f"Updated: {updated_count}/{len(articles)} articles")
            print(f"{'='*60}")

    except Exception as e:
        print(f"Error: {str(e)}")
        raise


if __name__ == '__main__':
    update_empty_summaries()
