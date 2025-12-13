"""
Appointment Service FastAPI Application.

This module initializes the FastAPI application with all middleware, routers, and configuration.
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

import api
from common.exceptions import HealthcareException
from common.logging import get_logger, setup_logging
from common.messaging.rabbitmq_publisher import RabbitMQPublisher
from common.middleware import (
    healthcare_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from config import get_settings
from database import engine, init_db


settings = get_settings()
setup_logging()
logger = get_logger(__name__)


# Prometheus Metrics
REQUEST_COUNT = Counter(
    "appointment_service_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "appointment_service_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Application lifespan handler.

    :param _app: FastAPI application instance
    """
    logger.info("appointment_service_starting")

    # Initialize database in thread pool to avoid async context issues
    await asyncio.to_thread(init_db)
    logger.info("database_initialized")

    yield

    logger.info("appointment_service_shutting_down")


# Initialize FastAPI application
app = FastAPI(
    title="Appointment Service",
    description="Healthcare Patient Management System - Appointment Microservice",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "syntaxHighlight.theme": "monokai",
        "url": "./openapi.json",
    },
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics Middleware
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """
    Middleware to collect Prometheus metrics.

    :param request: HTTP request
    :param call_next: Next middleware in chain
    :return: HTTP response
    """
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(
        duration
    )

    return response


# Exception Handlers
app.add_exception_handler(HealthcareException, healthcare_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


# Include API Router
app.include_router(api.router, prefix="/api/v1", tags=["Appointment Service"])


# Mount Prometheus Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint.

    :return: Welcome message
    """
    return {
        "service": "appointment-service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    :return: Service health status
    """
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check RabbitMQ connection with timeout
    rabbitmq_status = "disconnected"
    try:
        publisher = RabbitMQPublisher()
        await asyncio.wait_for(publisher.connect(), timeout=2.0)
        await publisher.close()
        rabbitmq_status = "connected"
    except asyncio.TimeoutError:
        rabbitmq_status = "timeout"
    except Exception:
        rabbitmq_status = "disconnected"

    return {
        "service": "appointment-service",
        "status": "healthy",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level=settings.log_level.lower(),
    )
