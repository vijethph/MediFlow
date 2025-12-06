"""
Appointment Service FastAPI Application.

This module initializes the FastAPI application with all middleware, routers, and configuration.
"""

import asyncio
import os
import sys
import time
from contextlib import asynccontextmanager

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.exceptions import HealthcareException
from common.logging import get_logger, setup_logging
from common.middleware import (
    healthcare_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from config import get_settings
from database import init_db, close_db

# Import all routers
from routers import appointments, advanced_search, batch_operations, analytics

# Try to import FHIR router (optional)
try:
    from routers import fhir_appointments

    FHIR_AVAILABLE = True
except ImportError:
    FHIR_AVAILABLE = False

settings = get_settings()
setup_logging(service_name=settings.service_name, log_level=settings.log_level)
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

    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise

    yield

    logger.info("appointment_service_shutting_down")
    await close_db()


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
        "url": "./openapi.json",  # Relative path for Kong proxy compatibility
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
async def metrics_middleware(request: Request, call_next):
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


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        correlation_id=correlation_id,
    )

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=round(process_time, 4),
        correlation_id=correlation_id,
    )

    return response


# Exception Handlers
app.add_exception_handler(HealthcareException, healthcare_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


# Include all routers
app.include_router(appointments.router)
app.include_router(advanced_search.router)
app.include_router(batch_operations.router)
app.include_router(analytics.router)

# Include FHIR router if available
if FHIR_AVAILABLE:
    app.include_router(fhir_appointments.router)
    logger.info("fhir_router_enabled")
else:
    logger.warning("fhir_router_disabled")


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
        "health": "/health",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    :return: Service health status
    """
    # Check database connection
    db_status = "disconnected"
    try:
        from database import engine
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning("database_health_check_failed", error=str(e))

    return {
        "service": "appointment-service",
        "status": "healthy",
        "database": db_status,
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
