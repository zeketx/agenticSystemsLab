"""Article content fetching service for extracting full content from web pages."""

import logging
import re
import requests
from bs4 import BeautifulSoup
import markdownify
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def fetch_article_content(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch full article content from URL and convert to markdown.

    Args:
        url: Full article URL

    Returns:
        Tuple of (content_markdown, error_message)
        - (markdown_string, None) on success
        - (None, error_string) on failure
    """
    try:
        # Fetch HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find article content
        content = soup.find('article')

        if not content:
            # Fallback to main tag
            content = soup.find('main')

        if not content:
            return None, "Could not find article or main content on page"

        # Remove noise elements from within the content
        for tag in content.find_all(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()

        # Convert to markdown using markdownify directly
        markdown = markdownify.markdownify(str(content))

        # Clean up markdown
        markdown = markdown.replace('\r\n', '\n').replace('\r', '\n')
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines).strip()

        if len(markdown) < 50:
            return None, "Extracted content too short"

        logger.debug(f"Successfully extracted {len(markdown)} chars of content")
        return markdown, None

    except requests.RequestException as e:
        return None, f"HTTP error: {str(e)}"
    except Exception as e:
        logger.error(f"Error fetching article content from {url}: {e}")
        return None, f"Error: {str(e)}"
