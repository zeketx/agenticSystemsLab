"""Models for aggregated content from multiple sources."""

from datetime import datetime
from typing import List, Union
from pydantic import BaseModel, Field

from app.scrapers import ArticleData, VideoData


class AggregationMetadata(BaseModel):
    """Metadata about a content aggregation run."""

    run_id: str = Field(
        ...,
        description="Unique identifier for this aggregation run (e.g., 'agg_20240118_143022')"
    )
    started_at: datetime = Field(..., description="When the aggregation started")
    completed_at: datetime = Field(..., description="When the aggregation completed")
    total_items: int = Field(default=0, ge=0, description="Total number of items aggregated")
    videos_count: int = Field(default=0, ge=0, description="Number of videos fetched")
    articles_count: int = Field(default=0, ge=0, description="Number of articles fetched")
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages encountered during aggregation"
    )
    sources_attempted: int = Field(default=0, ge=0, description="Number of sources attempted to fetch from")
    sources_succeeded: int = Field(default=0, ge=0, description="Number of sources successfully fetched from")

    model_config = {
        "validate_assignment": True,
    }

    @property
    def duration_seconds(self) -> float:
        """Calculate duration of aggregation run in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def has_errors(self) -> bool:
        """Check if any errors occurred during aggregation."""
        return len(self.errors) > 0

    @property
    def success_rate(self) -> float:
        """Calculate percentage of sources that succeeded."""
        if self.sources_attempted == 0:
            return 0.0
        return (self.sources_succeeded / self.sources_attempted) * 100


class AggregatedContent(BaseModel):
    """Container for all aggregated content from multiple sources."""

    metadata: AggregationMetadata = Field(..., description="Metadata about this aggregation run")
    videos: List[VideoData] = Field(default_factory=list, description="List of fetched YouTube videos")
    articles: List[ArticleData] = Field(default_factory=list, description="List of fetched blog articles")

    model_config = {
        "validate_assignment": True,
    }

    @property
    def all_content(self) -> List[Union[VideoData, ArticleData]]:
        """
        Get all content (videos and articles) combined and sorted by published date.

        Returns:
            List of all content items sorted by published_date (most recent first)
        """
        combined: List[Union[VideoData, ArticleData]] = []
        combined.extend(self.videos)
        combined.extend(self.articles)
        return sorted(combined, key=lambda x: x.published_date, reverse=True)

    @property
    def has_content(self) -> bool:
        """Check if any content was aggregated."""
        return len(self.videos) > 0 or len(self.articles) > 0

    def get_content_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Union[VideoData, ArticleData]]:
        """
        Filter content by date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of content items within the specified date range
        """
        return [
            item for item in self.all_content
            if start_date <= item.published_date <= end_date
        ]
