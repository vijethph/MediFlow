"""
Configuration Management for Billing Service.

This module defines environment-based configuration for the billing service.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = "billing-service"
    service_port: int = 8004
    environment: str = "development"
    log_level: str = "INFO"

    # Database Configuration
    database_url: str = (
        "postgresql://postgres:billing_secure_password@localhost:5432/billing_db"
    )

    # JWT Configuration
    jwt_secret: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # External Service URLs
    patient_service_url: str = "http://localhost:8001"
    appointment_service_url: str = "http://localhost:8002"

    # RabbitMQ Configuration
    rabbitmq_url: str = "amqp://admin:rabbitmq_secure_password@localhost:5672/"
    rabbitmq_exchange: str = "healthcare"
    rabbitmq_queue: str = "billing_queue"

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
