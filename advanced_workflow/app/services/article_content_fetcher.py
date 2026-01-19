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

        # Find article content - try multiple selectors
        content = None
        selector_used = None

        # Try semantic HTML tags first
        content = soup.find('article')
        if content:
            selector_used = '<article>'

        if not content:
            content = soup.find('main')
            if content:
                selector_used = '<main>'

        # Fallback to common content container patterns
        if not content:
            for selector in [
                {'class_': lambda x: x and 'content' in ' '.join(x).lower()},
                {'class_': lambda x: x and 'article' in ' '.join(x).lower()},
                {'class_': lambda x: x and 'post' in ' '.join(x).lower()},
                {'id': lambda x: x and 'content' in x.lower()},
            ]:
                content = soup.find('div', **selector)
                if content:
                    selector_used = f"div with {list(selector.keys())[0]}"
                    break

        # Last resort: find the div with the most text content
        if not content:
            divs = soup.find_all('div')
            if divs:
                # Filter out divs that are likely navigation/footer by checking text length
                text_divs = [(div, len(div.get_text(strip=True))) for div in divs]
                # Sort by text length and take the largest
                text_divs.sort(key=lambda x: x[1], reverse=True)
                if text_divs and text_divs[0][1] > 500:  # At least 500 chars
                    content = text_divs[0][0]
                    selector_used = 'largest text-containing div'

        if not content:
            return None, "Could not extract main content from page (tried: article, main, content divs, largest div)"

        logger.debug(f"Content extracted using selector: {selector_used}")

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
