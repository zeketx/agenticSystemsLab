# Feature: Anthropic Blog Scraper

## Feature Description
Implement a web scraper to collect articles from Anthropic's Research and Engineering blog pages (https://www.anthropic.com/research and https://www.anthropic.com/engineering). The scraper will extract article metadata including titles, publication dates, summaries, links, and subject tags. This extends the existing content collection capabilities beyond YouTube to include high-quality technical blog content from Anthropic's official channels.

## User Story
As a user of the AI News Aggregator
I want to automatically collect articles from Anthropic's Research and Engineering blogs
So that I can stay up-to-date with Anthropic's latest technical developments and research findings in my daily digest

## Problem Statement
The current system only supports YouTube video content via RSS feeds. Users interested in AI research and engineering developments need access to written content from authoritative sources like Anthropic's official blogs. These pages don't provide RSS feeds and require HTML scraping to extract article data. The system needs a reliable blog scraper that can extract structured article metadata from dynamic React-based pages.

## Solution Statement
Build an `AnthropicScraper` class that uses BeautifulSoup (already in dependencies) and requests to scrape article data from Anthropic's research and engineering pages. The scraper will:
1. Fetch HTML content from the target URLs
2. Parse article data from the page structure (which uses React/Sanity CMS)
3. Extract metadata including title, publication date, summary, slug/link, and subject tags
4. Return structured `ArticleData` dataclass objects matching the existing pattern from `YouTubeScraper`
5. Handle both featured articles and article list sections
6. Include proper error handling for network issues and parsing failures

## Relevant Files
Use these files to implement the feature:

### Existing Files
- **app/scrapers/youtube_scraper.py** - Reference implementation showing the existing scraper pattern using dataclasses, static methods, and error handling conventions to follow
- **app/scrapers/__init__.py** - Package initialization where the new scraper will be exposed
- **pyproject.toml** - Project dependencies (BeautifulSoup4 and requests already available)
- **test_youtube_scraper.py** - Testing pattern reference for creating the test file

### New Files
- **app/scrapers/anthropic_scraper.py** - New scraper implementation for Anthropic blog pages
- **test_anthropic_scraper.py** - Test script to validate the scraper functionality

## Implementation Plan

### Phase 1: Foundation
Create the core `ArticleData` dataclass structure and `AnthropicScraper` class skeleton following the existing `YouTubeScraper` pattern. Define the data model that will represent scraped articles with all necessary metadata fields.

### Phase 2: Core Implementation
Implement the HTML parsing logic to extract article data from both the research and engineering pages. Build methods to handle featured articles and article lists, parsing titles, dates, summaries, links, and tags from the page structure.

### Phase 3: Integration
Add proper error handling, validate the scraper works for both target URLs, create comprehensive tests, and ensure the new scraper integrates seamlessly with the existing scraper module structure.

## Step by Step Tasks

### 1. Create ArticleData dataclass and scraper skeleton
- Define `ArticleData` dataclass with fields: title, slug, url, published_date, summary, subjects (tags), source_type
- Create `AnthropicScraper` class with static methods following `YouTubeScraper` pattern
- Define base URLs as class constants for research and engineering pages
- Add proper docstrings and type hints

### 2. Implement HTML fetching and parsing infrastructure
- Create `_fetch_page_html(url: str) -> str` static method to retrieve page content
- Add user-agent headers to requests to avoid blocking
- Implement basic error handling for network requests (timeouts, HTTP errors)
- Create helper method `_parse_date(date_str: str) -> datetime` to handle date string parsing

### 3. Implement article extraction logic
- Create `_extract_articles_from_html(html: str, source_url: str) -> List[ArticleData]` method
- Use BeautifulSoup to parse HTML content
- Identify and extract article data from page structure (handle both featured and list items)
- Parse title, date, summary, slug, and subject tags from HTML elements
- Build complete URLs from slugs using base domain

### 4. Create public API methods
- Implement `fetch_research_articles(max_results: int = 20) -> List[ArticleData]` method
- Implement `fetch_engineering_articles(max_results: int = 20) -> List[ArticleData]` method
- Implement `fetch_all_articles(max_results: int = 20) -> List[ArticleData]` to get from both sources
- Add proper error handling and logging for each method

### 5. Create comprehensive test file
- Create `test_anthropic_scraper.py` following the pattern from `test_youtube_scraper.py`
- Write test function for research articles
- Write test function for engineering articles
- Write test function for fetching all articles
- Include error case handling tests
- Display extracted data in readable format for manual validation

### 6. Update package exports
- Add `AnthropicScraper` and `ArticleData` to `app/scrapers/__init__.py`
- Ensure clean import structure for the new scraper

### 7. Run validation commands
- Execute test script to verify scraper works correctly
- Validate data extraction from both research and engineering pages
- Check that all article fields are populated correctly
- Ensure no errors or exceptions during normal operation

### Edge Cases
- Empty or malformed HTML response
- Missing publication dates
- Articles without summaries or tags
- Network timeout scenarios
- HTTP error responses (404, 500, etc.)
- Changes to page structure (graceful degradation)
- Unicode and special characters in article content

## Acceptance Criteria
- [ ] `AnthropicScraper` class successfully scrapes articles from https://www.anthropic.com/research
- [ ] `AnthropicScraper` class successfully scrapes articles from https://www.anthropic.com/engineering
- [ ] Extracted `ArticleData` includes: title, slug, url, published_date, summary, subjects, and source_type
- [ ] Scraper handles both featured articles and article list items
- [ ] Proper error handling for network failures and parsing errors
- [ ] Test script runs without errors and displays article data correctly
- [ ] Code follows existing patterns from `YouTubeScraper` (dataclasses, static methods, docstrings)
- [ ] All article URLs are valid and clickable
- [ ] Publication dates are correctly parsed to datetime objects
- [ ] Subject tags are extracted and stored as lists

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `python test_anthropic_scraper.py` - Run the scraper test to validate it extracts articles from both research and engineering pages
- `python -c "from app.scrapers.anthropic_scraper import AnthropicScraper, ArticleData; articles = AnthropicScraper.fetch_research_articles(5); print(f'Fetched {len(articles)} research articles'); assert len(articles) > 0"` - Quick validation that research scraping works
- `python -c "from app.scrapers.anthropic_scraper import AnthropicScraper, ArticleData; articles = AnthropicScraper.fetch_engineering_articles(5); print(f'Fetched {len(articles)} engineering articles'); assert len(articles) > 0"` - Quick validation that engineering scraping works
- `python -c "from app.scrapers import AnthropicScraper; print('Import successful')"` - Verify package exports work correctly

## Notes
- **Dependencies**: BeautifulSoup4 and requests are already in `pyproject.toml`, no new packages needed
- **Page Structure**: Both pages use React/Next.js with Sanity CMS backend. Articles are rendered in the HTML, so no JavaScript execution needed
- **Data Source**: Articles are embedded in the page HTML structure, making them scrapable without API access
- **Rate Limiting**: Consider adding delays between requests if scraping multiple pages to be respectful to Anthropic's servers
- **Future Considerations**:
  - The page structure may change over time; scraper should fail gracefully
  - Could add caching to avoid re-scraping the same content
  - Could extend to other blog sources using similar patterns
  - May want to extract image URLs for article thumbnails in future iterations
- **Article Links**: URLs are built from slugs in format: `https://www.anthropic.com/research/{slug}` or `https://www.anthropic.com/engineering/{slug}`
