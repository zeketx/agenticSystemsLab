"""Database schema initialization."""

from pathlib import Path
from sqlalchemy import text
from app.database.connections import engine


def create_tables():
    """Execute init.sql to create database tables."""
    sql = Path("scripts/init.sql").read_text()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
