"""Configuration module for AI News Aggregator."""

from app.config.config_loader import (
    BlogConfig,
    BlogSourceConfig,
    SettingsConfig,
    SourcesConfig,
    YouTubeChannelConfig,
    load_sources_config,
)

__all__ = [
    "load_sources_config",
    "SourcesConfig",
    "YouTubeChannelConfig",
    "BlogSourceConfig",
    "BlogConfig",
    "SettingsConfig",
]
