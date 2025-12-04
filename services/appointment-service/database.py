"""
Database Configuration and Session Management.

This module manages SQLAlchemy async database connections and sessions.
"""

import os
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from common.logging import get_logger
from config import get_settings


settings = get_settings()
logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.

    Yields database session and ensures it's closed after use.

    :yield: SQLAlchemy async database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models.
    """
    import asyncio
    import time
    max_retries = 15
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt}/{max_retries})")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.warning(f"Database connection failed (attempt {attempt}/{max_retries}): {str(e)}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Failed to connect to database after all retries")
                raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

