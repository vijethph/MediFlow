"""Rate limiting middleware."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from config import settings

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],
    storage_uri="memory://"  # Use Redis in production: f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
)

# Rate limit configurations
RATE_LIMITS = {
    "register": "10/hour",  # Registration endpoint
    "login": "20/hour",     # Login endpoint
    "default": "1000/hour", # Default for other endpoints
    "search": "200/hour",   # Search endpoints
}


def get_rate_limit_for_endpoint(endpoint: str) -> str:
    """
    Get rate limit for specific endpoint.
    
    Args:
        endpoint: API endpoint path
        
    Returns:
        Rate limit string
    """
    if "register" in endpoint:
        return RATE_LIMITS["register"]
    elif "login" in endpoint:
        return RATE_LIMITS["login"]
    elif "search" in endpoint or "list" in endpoint:
        return RATE_LIMITS["search"]
    else:
        return RATE_LIMITS["default"]


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": 60
        }
    )

