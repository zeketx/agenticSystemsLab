"""Configuration loader with Pydantic validation for sources.yaml."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class YouTubeChannelConfig(BaseModel):
    """Configuration for a single YouTube channel."""

    id: str = Field(
        ...,
        pattern=r'^UC[a-zA-Z0-9_-]{22}$',
        description="YouTube channel ID (UC followed by 22 characters)"
    )
    name: str = Field(..., min_length=1, max_length=200, description="Channel display name")
    enabled: bool = Field(default=True, description="Whether to fetch videos from this channel")
    max_results: int = Field(default=15, ge=1, le=50, description="Maximum number of videos to fetch")

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }

    @field_validator("name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace from name."""
        return v.strip()


class BlogSourceConfig(BaseModel):
    """Configuration for a single blog source."""

    type: str = Field(..., min_length=1, max_length=50, description="Source type identifier")
    url: HttpUrl = Field(..., description="Blog URL to scrape")
    max_results: int = Field(default=20, ge=1, le=50, description="Maximum number of articles to fetch")
    enabled: bool = Field(default=True, description="Whether to fetch articles from this source")

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


class BlogConfig(BaseModel):
    """Configuration for a blog aggregator (e.g., Anthropic, OpenAI)."""

    enabled: bool = Field(default=True, description="Whether to fetch from this blog aggregator")
    sources: List[BlogSourceConfig] = Field(default_factory=list, description="List of sources to scrape")

    model_config = {
        "validate_assignment": True,
    }


class SettingsConfig(BaseModel):
    """Global settings for content aggregation."""

    fetch_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="HTTP request timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of retry attempts for failed requests"
    )
    user_interests: List[str] = Field(
        default_factory=list,
        description="User interests for personalized digest generation"
    )

    model_config = {
        "validate_assignment": True,
    }


class SourcesConfig(BaseModel):
    """Root configuration model for all content sources."""

    youtube: Dict[str, List[YouTubeChannelConfig]] = Field(
        default_factory=dict,
        description="YouTube channel configurations"
    )
    blogs: Dict[str, BlogConfig] = Field(
        default_factory=dict,
        description="Blog source configurations"
    )
    settings: SettingsConfig = Field(
        default_factory=SettingsConfig,
        description="Global aggregation settings"
    )

    model_config = {
        "validate_assignment": True,
    }


def load_sources_config(config_path: Optional[str] = None) -> SourcesConfig:
    """
    Load and validate sources configuration from YAML file.

    Args:
        config_path: Optional path to sources.yaml file.
                    If not provided, searches for config/sources.yaml in project root.

    Returns:
        SourcesConfig: Validated configuration object

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValidationError: If configuration doesn't match schema
    """
    # Determine config file path
    if config_path is None:
        # Try config/sources.yaml relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "sources.yaml"

        if not config_path.exists():
            # Try sources.yaml in project root as fallback
            config_path = project_root / "sources.yaml"
    else:
        config_path = Path(config_path)

    # Check if file exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Expected location: config/sources.yaml in project root"
        )

    # Load YAML file
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML configuration: {e}")

    # Handle empty file
    if config_data is None:
        config_data = {}

    # Validate and return configuration
    return SourcesConfig(**config_data)
