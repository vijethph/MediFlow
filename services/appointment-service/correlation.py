"""Correlation ID middleware for request tracking."""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add correlation ID to request and response."""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response

