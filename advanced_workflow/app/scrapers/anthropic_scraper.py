"""Anthropic blog scraper for fetching articles from Research and Engineering pages."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, HttpUrl


class ArticleData(BaseModel):
    """Anthropic blog article metadata with validation."""

    title: str = Field(..., min_length=1, max_length=500, description="Article title")
    slug: str = Field(..., min_length=1, max_length=200, pattern=r'^[a-zA-Z0-9-_]+$', description="URL slug")
    url: HttpUrl = Field(..., description="Full article URL")
    published_date: datetime
    summary: str = Field(default="", max_length=5000, description="Article summary/excerpt")
    subjects: list[str] = Field(default_factory=list, description="Article tags/subjects")
    source_type: Literal['research', 'engineering'] = Field(..., description="Blog source type")

    @field_validator('url')
    @classmethod
    def validate_anthropic_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL is from Anthropic domain."""
        url_str = str(v)
        if 'anthropic.com' not in url_str:
            raise ValueError('URL must be from anthropic.com domain')
        return v

    @field_validator('title', 'summary')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading/trailing whitespace."""
        return v.strip()

    @field_validator('subjects')
    @classmethod
    def validate_subjects(cls, v: list[str]) -> list[str]:
        """Ensure subject tags are cleaned and deduplicated."""
        # Strip whitespace from each subject and remove empty strings
        cleaned = [s.strip() for s in v if s and s.strip()]
        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for subject in cleaned:
            if subject.lower() not in seen:
                seen.add(subject.lower())
                deduped.append(subject)
        return deduped

    model_config = {
        'str_strip_whitespace': True,
        'validate_assignment': True,
    }


class AnthropicScraper:
    """Scraper for fetching articles from Anthropic's Research and Engineering blogs."""

    RESEARCH_URL = "https://www.anthropic.com/research"
    ENGINEERING_URL = "https://www.anthropic.com/engineering"
    BASE_DOMAIN = "https://www.anthropic.com"

    @staticmethod
    def _fetch_page_html(url: str) -> str:
        """
        Fetch HTML content from a given URL.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as string

        Raises:
            Exception: If request fails or times out
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.Timeout:
            raise Exception(f"Request timeout while fetching {url}")
        except requests.HTTPError as e:
            raise Exception(f"HTTP error fetching {url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error fetching {url}: {str(e)}")

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """
        Parse date string to datetime object.

        Args:
            date_str: Date string in various formats

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If date cannot be parsed
        """
        date_formats = [
            "%B %d, %Y",      # January 15, 2024
            "%b %d, %Y",       # Jan 15, 2024
            "%Y-%m-%d",        # 2024-01-15
            "%m/%d/%Y",        # 01/15/2024
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        raise ValueError(f"Could not parse date: {date_str}")

    @staticmethod
    def _extract_articles_from_html(html: str, source_url: str) -> list[ArticleData]:
        """
        Extract article data from HTML content.

        Args:
            html: HTML content to parse
            source_url: Source URL (research or engineering)

        Returns:
            List of ArticleData objects
        """
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        source_type = 'research' if 'research' in source_url else 'engineering'

        # Find all links to articles (exclude team/category pages)
        article_links = soup.find_all('a', href=lambda x: x and f'/{source_type}/' in x and '/team/' not in x)

        # Track processed URLs to avoid duplicates
        seen_urls = set()

        for link in article_links:
            try:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue

                # Build full URL and slug
                if href.startswith('/'):
                    url = f"{AnthropicScraper.BASE_DOMAIN}{href}"
                    slug = href.split('/')[-1]
                else:
                    url = href
                    slug = href.split('/')[-1]

                # Skip if already processed
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Find the parent container for this article
                parent = link.find_parent('div')
                if not parent:
                    continue

                # Extract title - look for heading elements closest to this specific link
                # First try to find a heading that contains this link
                title_elem = None
                for heading in parent.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    # Check if this heading contains our link or is near it
                    if link in heading.find_all('a') or heading.find('a', href=href):
                        title_elem = heading
                        break

                # If no heading contains the link, get the link's text as title
                if not title_elem:
                    title = link.get_text(strip=True)
                    # Clean up the title - remove date and tag text
                    # Title format is often like "TagDateTitle" so we need to extract just the title part
                    if len(title) > 100:
                        # If very long, try to find heading near link
                        title_elem = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                    elif len(title) < 5:
                        continue
                else:
                    title = title_elem.get_text(strip=True)

                # Extract date - look for time element
                date_elem = parent.find('time')
                if not date_elem:
                    # Try broader search up the tree
                    container = parent.find_parent('div')
                    if container:
                        date_elem = container.find('time')

                published_date = None
                if date_elem:
                    date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                    try:
                        # Try ISO format first
                        if 'T' in date_str:
                            published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            published_date = AnthropicScraper._parse_date(date_str)
                    except Exception:
                        pass

                # If no date found, use a default date (current time)
                # This allows us to still capture articles from pages without dates
                if not published_date:
                    published_date = datetime.now()

                # Extract summary/description
                summary = ""
                # Look for paragraphs in the parent container
                paragraphs = parent.find_all('p')
                if paragraphs:
                    # Take the first substantial paragraph
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 20:  # Ensure it's substantial
                            summary = text
                            break

                # Extract subject tags - look for common tag patterns
                subjects = []
                # Try to find tag/category containers
                tag_containers = parent.find_all(['div', 'span', 'ul'], class_=lambda x: x and ('tag' in str(x).lower() or 'category' in str(x).lower() or 'label' in str(x).lower()))
                for container in tag_containers:
                    tag_elements = container.find_all(['span', 'a', 'li'])
                    for tag in tag_elements:
                        tag_text = tag.get_text(strip=True)
                        if tag_text and len(tag_text) < 50:  # Reasonable tag length
                            subjects.append(tag_text)

                article = ArticleData(
                    title=title,
                    slug=slug,
                    url=url,
                    published_date=published_date,
                    summary=summary,
                    subjects=subjects,
                    source_type=source_type
                )

                articles.append(article)

            except Exception:
                # Skip articles that fail to parse
                continue

        return articles

    @staticmethod
    def fetch_research_articles(max_results: int = 20) -> list[ArticleData]:
        """
        Fetch articles from Anthropic's Research blog.

        Args:
            max_results: Maximum number of articles to return

        Returns:
            List of ArticleData objects from research blog
        """
        try:
            html = AnthropicScraper._fetch_page_html(AnthropicScraper.RESEARCH_URL)
            articles = AnthropicScraper._extract_articles_from_html(html, AnthropicScraper.RESEARCH_URL)
            return articles[:max_results]
        except Exception as e:
            raise Exception(f"Error fetching research articles: {str(e)}")

    @staticmethod
    def fetch_engineering_articles(max_results: int = 20) -> list[ArticleData]:
        """
        Fetch articles from Anthropic's Engineering blog.

        Args:
            max_results: Maximum number of articles to return

        Returns:
            List of ArticleData objects from engineering blog
        """
        try:
            html = AnthropicScraper._fetch_page_html(AnthropicScraper.ENGINEERING_URL)
            articles = AnthropicScraper._extract_articles_from_html(html, AnthropicScraper.ENGINEERING_URL)
            return articles[:max_results]
        except Exception as e:
            raise Exception(f"Error fetching engineering articles: {str(e)}")

    @staticmethod
    def fetch_all_articles(max_results: int = 20) -> list[ArticleData]:
        """
        Fetch articles from both Research and Engineering blogs.

        Args:
            max_results: Maximum number of articles to return from each source

        Returns:
            Combined list of ArticleData objects from both blogs, sorted by published date
        """
        try:
            research_articles = AnthropicScraper.fetch_research_articles(max_results)
            engineering_articles = AnthropicScraper.fetch_engineering_articles(max_results)

            all_articles = research_articles + engineering_articles
            # Sort by published date, most recent first
            all_articles.sort(key=lambda x: x.published_date, reverse=True)

            return all_articles
        except Exception as e:
            raise Exception(f"Error fetching all articles: {str(e)}")
