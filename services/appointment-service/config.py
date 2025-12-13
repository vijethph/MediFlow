"""
Configuration Management.

This module handles application configuration using pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = "appointment-service"
    service_port: int = 8002
    environment: str = "development"
    log_level: str = "INFO"

    # Database Configuration
    database_url: str = (
        "postgresql://postgres:appointment_secure_password@localhost:5432/appointment_db"
    )

    # JWT Configuration
    JWT_SECRET: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # External Service URLs
    patient_service_url: str = "http://localhost:8001"

    # RabbitMQ Configuration
    rabbitmq_url: str = "amqp://admin:rabbitmq_secure_password@localhost:5672/"
    rabbitmq_exchange: str = "healthcare"
    rabbitmq_queue: str = "appointment_queue"

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    :return: Settings object with all configuration
    """
    return Settings()
