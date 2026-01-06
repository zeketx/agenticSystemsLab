"""Database module for content storage with deduplication."""

from app.database.repository import save_video, save_article, save_all

__all__ = ['save_video', 'save_article', 'save_all']
