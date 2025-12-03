"""
Global Error Handlers for FastAPI Applications.

This module provides centralized error handling middleware.
"""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.exceptions import HealthcareException
from common.logging.logger_config import get_logger


logger = get_logger(__name__)


def healthcare_exception_handler(request: Request, exc: HealthcareException):
    """
    Handle custom healthcare exceptions.

    :param request: FastAPI request object
    :param exc: Healthcare exception
    :return: JSON response with error details
    """
    logger.error(
        "healthcare_exception",
        exception_type=type(exc).__name__,
        detail=str(exc),
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "path": str(request.url.path),
        },
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.

    :param request: FastAPI request object
    :param exc: Validation error
    :return: JSON response with validation error details
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        body=exc.body,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "detail": exc.errors(),
            "body": exc.body,
            "path": str(request.url.path),
        },
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions.

    :param request: FastAPI request object
    :param exc: HTTP exception
    :return: JSON response with error details
    """
    logger.error(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )


def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Handle unhandled exceptions.

    :param request: FastAPI request object
    :param exc: Unhandled exception
    :return: JSON response with error details
    """
    logger.error(
        "unhandled_exception",
        exception_type=type(exc).__name__,
        detail=str(exc),
        path=request.url.path,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": "An unexpected error occurred. Please contact support.",
            "path": str(request.url.path),
        },
    )


def register_error_handlers(app):
    """
    Register all error handlers with FastAPI application.

    :param app: FastAPI application instance
    """
    app.add_exception_handler(HealthcareException, healthcare_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
