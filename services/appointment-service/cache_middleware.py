"""Caching middleware for request/response caching."""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import hashlib
import json
from cache import get_cache, set_cache
from config import settings
import logging

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching GET requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Cache GET requests based on URL and query parameters."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Skip caching for certain endpoints
        skip_cache_paths = ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_cache_paths):
            return await call_next(request)
        
        # Generate cache key from request
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        if settings.ENABLE_CACHING:
            cached_response = await get_cache(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {cache_key}")
                return Response(
                    content=json.dumps(cached_response["data"]),
                    status_code=cached_response["status_code"],
                    headers=cached_response.get("headers", {}),
                    media_type="application/json"
                )
        
        # Process request
        response = await call_next(request)
        
        # Cache successful GET responses
        if settings.ENABLE_CACHING and response.status_code == 200:
            try:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parse JSON if possible
                try:
                    response_data = json.loads(response_body.decode()) if response_body else None
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Not JSON, skip caching
                    response_data = None
                
                if response_data:
                    cache_data = {
                        "data": response_data,
                        "status_code": response.status_code,
                        "headers": dict(response.headers)
                    }
                    # Cache for shorter TTL for dynamic data
                    cache_ttl = 300 if "search" in request.url.path or "list" in request.url.path else 1800
                    await set_cache(cache_key, cache_data, ttl=cache_ttl)
                    logger.debug(f"Cached response for {cache_key}")
                
                # Recreate response with body
                from starlette.responses import Response
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
            except Exception as e:
                logger.error(f"Failed to cache response: {e}")
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        key_string = "|".join(key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"appointment:cache:{key_hash}"

