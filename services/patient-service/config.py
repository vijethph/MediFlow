"""
Configuration Management.

This module handles application configuration using pydantic-settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = "patient-service"
    service_port: int = 8001
    environment: str = "development"
    log_level: str = "INFO"

    # Database Configuration
    database_url: str = (
        "postgresql://postgres:patient_secure_password@localhost:5432/patient_db"
    )

    # JWT Configuration
    JWT_SECRET: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # RabbitMQ Configuration
    rabbitmq_url: str = "amqp://admin:rabbitmq_secure_password@localhost:5672/"
    rabbitmq_exchange: str = "healthcare"
    rabbitmq_queue: str = "patient_queue"

    # Redis Configuration
    redis_url: str = "redis://:redis_secure_password@localhost:6379/0"
    redis_enabled: bool = False

    # API Configuration
    api_v1_prefix: str = "/api/v1"

    # Cache Configuration
    cache_ttl: int = 300  # 5 minutes

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
