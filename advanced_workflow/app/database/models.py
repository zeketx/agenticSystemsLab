"""SQLAlchemy table definitions."""

from sqlalchemy import Table, Column, Integer, String, Text, TIMESTAMP, ARRAY, MetaData

metadata = MetaData()

videos = Table('videos', metadata,
    Column('id', Integer, primary_key=True),
    Column('video_id', String(11), unique=True, nullable=False),
    Column('title', Text, nullable=False),
    Column('channel_name', String(200)),
    Column('channel_id', String(24)),
    Column('published_at', TIMESTAMP),
    Column('link', Text),
    Column('description', Text),
    Column('transcript_text', Text),
    Column('created_at', TIMESTAMP, server_default='NOW()')
)

articles = Table('articles', metadata,
    Column('id', Integer, primary_key=True),
    Column('url', Text, unique=True, nullable=False),
    Column('title', Text, nullable=False),
    Column('slug', String(255)),
    Column('published_at', TIMESTAMP),
    Column('summary', Text),
    Column('subjects', ARRAY(Text)),
    Column('created_at', TIMESTAMP, server_default='NOW()')
)
