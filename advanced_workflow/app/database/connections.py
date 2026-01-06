"""Database connection setup."""

import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://newsagg:newsagg@localhost:5432/newsagg"
)
engine = create_engine(DATABASE_URL)
