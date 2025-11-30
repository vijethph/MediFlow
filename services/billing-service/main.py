"""
Billing Service FastAPI Application.

This module initializes the FastAPI application with all middleware, routers, and configuration.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, make_asgi_app
import time

from config import get_settings
from database import init_db
import api
from common.logging import setup_logging, get_logger
from common.middleware import (
    healthcare_exception_handler,
    validation_exception_handler,
    http_exception_handler,
)
from common.exceptions import HealthcareException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


settings = get_settings()
setup_logging()
logger = get_logger(__name__)


# Prometheus Metrics
REQUEST_COUNT = Counter(
    "billing_service_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "billing_service_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Application lifespan handler.

    :param _app: FastAPI application instance
    """
    logger.info("billing_service_starting")

    # Initialize database
    init_db()
    logger.info("database_initialized")

    yield

    logger.info("billing_service_shutting_down")


# Initialize FastAPI application
app = FastAPI(
    title="Billing Service",
    description="Healthcare Patient Management System - Billing Microservice",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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
app.include_router(api.router, prefix="/api/v1", tags=["Billing Service"])


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
        "service": "billing-service",
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
    from database import engine
    from common.messaging.rabbitmq_publisher import RabbitMQPublisher

    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check RabbitMQ connection
    try:
        publisher = RabbitMQPublisher()
        await publisher.connect()
        await publisher.close()
        rabbitmq_status = "connected"
    except Exception:
        rabbitmq_status = "disconnected"

    return {
        "service": "billing-service",
        "status": "healthy",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level=settings.log_level.lower(),
    )
