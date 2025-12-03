"""
Structured Logging Configuration using structlog.

This module sets up structured logging for the healthcare system.
"""

from typing import Any

import structlog


def setup_logging(
    service_name: str = "healthcare-service", log_level: str = "INFO"
) -> None:
    """
    Configure structured logging with structlog.

    :param service_name: Name of the service for logging context
    :param log_level: Logging level
    """
    _ = service_name
    _ = log_level

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.

    :param name: Logger name (typically __name__ of the module)
    :return: Configured logger instance
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **kwargs: Any
) -> None:
    """
    Log API request with structured format.

    :param logger: structlog logger instance
    :param method: HTTP method
    :param path: Request path
    :param status_code: Response status code
    :param duration: Request duration in seconds
    :param kwargs: Additional context
    """
    logger.info(
        "api_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_seconds=round(duration, 4),
        **kwargs
    )


def log_database_query(
    logger: structlog.BoundLogger,
    operation: str,
    table: str,
    duration: float,
    **kwargs: Any
) -> None:
    """
    Log database query with structured format.

    :param logger: structlog logger instance
    :param operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
    :param table: Table name
    :param duration: Query duration in seconds
    :param kwargs: Additional context
    """
    logger.info(
        "database_query",
        operation=operation,
        table=table,
        duration_seconds=round(duration, 4),
        **kwargs
    )


def log_event(
    logger: structlog.BoundLogger, event_type: str, event_name: str, **kwargs: Any
) -> None:
    """
    Log system event with structured format.

    :param logger: structlog logger instance
    :param event_type: Type of event (rabbitmq, internal, external)
    :param event_name: Event name
    :param kwargs: Additional context
    """
    logger.info("system_event", event_type=event_type, event_name=event_name, **kwargs)


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: str | None = None,
    **kwargs: Any
) -> None:
    """
    Log error with structured format.

    :param logger: structlog logger instance
    :param error: Exception object
    :param context: Error context description
    :param kwargs: Additional context
    """
    logger.error(
        "error_occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        **kwargs,
        exc_info=True
    )
