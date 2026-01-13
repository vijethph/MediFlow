"""
Configuration Management for Prescription Service.

This module handles application configuration using pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = "prescription-service"
    service_port: int = 8003
    environment: str = "development"
    log_level: str = "INFO"

    # MongoDB Configuration
    mongo_url: str = (
        "mongodb://admin:mongo_secure_password@localhost:27017/"
        "prescription_db?authSource=admin"
    )
    mongo_database: str = "prescription_db"

    # JWT Configuration
    JWT_SECRET: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # External Service URLs
    patient_service_url: str = "http://localhost:8001"
    appointment_service_url: str = "http://localhost:8002"

    # RabbitMQ Configuration
    rabbitmq_url: str = "amqp://admin:rabbitmq_secure_password@localhost:5672/"
    rabbitmq_exchange: str = "healthcare"
    rabbitmq_queue: str = "prescription_queue"

    # Redis Configuration
    redis_url: str = "redis://:redis_secure_password@localhost:6379/2"

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    # File Storage
    max_file_size_mb: int = 10
    allowed_file_types: list = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/dicom",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    :return: Settings object with all configuration
    """
    return Settings()
