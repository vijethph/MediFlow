"""
Database Configuration and Session Management for MongoDB.

This module manages MongoDB connections and database sessions.
"""

import time
from typing import Generator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from common.logging import get_logger
from config import get_settings

settings = get_settings()
logger = get_logger(__name__)

# MongoDB Client (synchronous)
mongo_client: MongoClient = None
db: MongoClient = None

# Motor Client (asynchronous)
motor_client: AsyncIOMotorClient = None
async_db: AsyncIOMotorDatabase = None


def get_database() -> MongoClient:
    """
    Get synchronous MongoDB database instance.

    :return: MongoDB database
    """
    global mongo_client, db

    if db is None:
        mongo_client = MongoClient(settings.mongo_url)
        db = mongo_client[settings.mongo_database]
        logger.info("mongodb_connected", database=settings.mongo_database)

    return db


def get_async_database() -> AsyncIOMotorDatabase:
    """
    Get asynchronous MongoDB database instance.

    :return: Motor AsyncIOMotorDatabase
    """
    global motor_client, async_db

    if async_db is None:
        motor_client = AsyncIOMotorClient(settings.mongo_url)
        async_db = motor_client[settings.mongo_database]
        logger.info("mongodb_async_connected", database=settings.mongo_database)

    return async_db


def get_db() -> Generator[MongoClient, None, None]:
    """
    Dependency for getting database session.

    Yields database and ensures proper connection management.

    :yield: MongoDB database instance
    """
    database = get_database()
    try:
        yield database
    finally:
        pass  # MongoDB handles connection pooling automatically


async def get_async_db() -> AsyncIOMotorDatabase:
    """
    Dependency for getting async database session.

    :return: Motor AsyncIOMotorDatabase
    """
    return get_async_database()


def init_db() -> None:
    """
    Initialize database and create collections/indexes.

    Creates collections and indexes if they don't exist.
    Retries connection if database is not ready yet.
    """
    max_retries = 15
    retry_delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Attempting to connect to MongoDB (attempt {attempt}/{max_retries})"
            )

            # Test connection
            client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            database = client[settings.mongo_database]

            # Create collections if they don't exist
            existing_collections = database.list_collection_names()

            if "prescriptions" not in existing_collections:
                database.create_collection("prescriptions")
                logger.info("created_collection", collection="prescriptions")

            if "medical_records" not in existing_collections:
                database.create_collection("medical_records")
                logger.info("created_collection", collection="medical_records")

            if "lab_results" not in existing_collections:
                database.create_collection("lab_results")
                logger.info("created_collection", collection="lab_results")

            # Create indexes
            database.prescriptions.create_index("prescription_id", unique=True)
            database.prescriptions.create_index("patient_id")
            database.prescriptions.create_index("appointment_id")
            database.prescriptions.create_index("created_at")

            database.medical_records.create_index("record_id", unique=True)
            database.medical_records.create_index("patient_id")
            database.medical_records.create_index("created_at")

            database.lab_results.create_index("result_id", unique=True)
            database.lab_results.create_index("patient_id")
            database.lab_results.create_index("test_date")

            logger.info("Database indexes created successfully")

            client.close()
            return

        except ConnectionFailure as e:
            logger.warning(
                f"MongoDB connection failed (attempt {attempt}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Failed to connect to MongoDB after all retries")
                raise


def close_db() -> None:
    """Close MongoDB connections."""
    global mongo_client, motor_client

    if mongo_client:
        mongo_client.close()
        logger.info("mongodb_connection_closed")

    if motor_client:
        motor_client.close()
        logger.info("mongodb_async_connection_closed")