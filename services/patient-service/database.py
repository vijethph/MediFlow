"""
Database Configuration and Session Management.

This module manages SQLAlchemy database connections and sessions.
"""

from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings


settings = get_settings()

database_url = settings.database_url
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://", 1
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.environment == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session.

    Yields database session and ensures it's closed after use.

    :yield: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models.
    Retries connection if database is not ready yet.
    """
    import time
    from common.logging import get_logger

    logger = get_logger(__name__)
    max_retries = 15
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Attempting to connect to database (attempt {attempt}/{max_retries})"
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return

        except Exception as e:
            logger.warning(
                f"Database connection failed (attempt {attempt}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to database after all retries")
                raise
