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
        "postgresql+asyncpg://postgres:appointment_secure_password@localhost:5432/appointment_db"
    )

    # JWT Configuration
    jwt_secret: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # External Service URLs
    patient_service_url: str = "http://localhost:8001"

    # RabbitMQ Configuration
    rabbitmq_url: str = "amqp://admin:rabbitmq_secure_password@localhost:5672/"
    rabbitmq_exchange: str = "healthcare"
    rabbitmq_queue: str = "appointment_queue"

    # Redis Configuration
    redis_url: str = "redis://:redis_secure_password@localhost:6379/1"
    redis_enabled: bool = False

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    # Appointment-specific settings
    appointment_duration_minutes: int = 30
    max_advance_booking_days: int = 90
    min_advance_booking_hours: int = 24

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


# Export settings instance for backward compatibility
settings = get_settings()

