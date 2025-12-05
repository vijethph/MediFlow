"""Correlation ID middleware for request tracking."""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add correlation ID to request and response."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response header
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response

