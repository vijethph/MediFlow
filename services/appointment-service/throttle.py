"""Request throttling middleware."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseHTTPMiddleware):
    """Middleware for request throttling per user/IP."""
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        """
        Initialize throttle middleware.
        
        Args:
            app: FastAPI application
            requests_per_minute: Maximum requests per minute
            requests_per_hour: Maximum requests per hour
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.request_times: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next):
        """Throttle requests based on IP address."""
        # Get client identifier
        client_id = self._get_client_id(request)
        
        async with self._lock:
            now = datetime.utcnow()
            
            # Clean old entries
            if client_id in self.request_times:
                # Remove entries older than 1 hour
                self.request_times[client_id] = [
                    t for t in self.request_times[client_id]
                    if (now - t).total_seconds() < 3600
                ]
            else:
                self.request_times[client_id] = []
            
            # Check per-minute limit
            recent_requests = [
                t for t in self.request_times[client_id]
                if (now - t).total_seconds() < 60
            ]
            
            if len(recent_requests) >= self.requests_per_minute:
                logger.warning(f"Throttle limit exceeded for {client_id}: {len(recent_requests)} requests in last minute")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "message": f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                        "retry_after": 60
                    }
                )
            
            # Check per-hour limit
            hourly_requests = [
                t for t in self.request_times[client_id]
                if (now - t).total_seconds() < 3600
            ]
            
            if len(hourly_requests) >= self.requests_per_hour:
                logger.warning(f"Throttle limit exceeded for {client_id}: {len(hourly_requests)} requests in last hour")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "message": f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                        "retry_after": 3600
                    }
                )
            
            # Record request
            self.request_times[client_id].append(now)
        
        # Process request
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get user ID from token
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        return f"ip:{request.client.host if request.client else 'unknown'}"

