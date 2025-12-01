"""
JWT Token Handler for Authentication and Authorization.

This module provides utilities for JWT token validation and user context extraction.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt


JWT_SECRET = os.getenv(
    "JWT_SECRET", "your-super-secret-jwt-key-change-this-in-production"
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


class JWTBearer(HTTPBearer):
    """
    JWT Bearer token validator for FastAPI dependency injection.

    Usage:
        @app.get("/protected", dependencies=[Depends(JWTBearer())])
        async def protected_route():
            return {"message": "Protected route"}
    """

    def __init__(self, auto_error: bool = True):
        """
        Initialize JWT Bearer validator.

        :param auto_error: Raise HTTPException if validation fails
        """
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token from Authorization header.

        :param request: FastAPI request object
        :return: Decoded JWT payload
        :raises HTTPException: If token is invalid or missing
        """
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)

        if credentials:
            if credentials.scheme != "Bearer":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme",
                )

            payload = decode_jwt(credentials.credentials)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token or expired token",
                )

            request.state.user = payload
            return payload
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code",
            )


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.

    :param data: Payload data to encode in token
    :param expires_delta: Token expiration time delta
    :return: Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)

    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "iss": "healthcare-system"}
    )

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate JWT token.

    :param token: JWT token string
    :return: Decoded payload or None if invalid
    """
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if (
            "exp" in decoded_token
            and decoded_token["exp"] < datetime.now(timezone.utc).timestamp()
        ):
            raise HTTPException(status_code=401, detail="Token expired")

        return decoded_token
    except JWTError:
        return None


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Extract current user from request state.

    :param request: FastAPI request object
    :return: User payload from JWT token
    :raises HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return request.state.user


def require_role(required_roles: list[str]):
    """
    Decorator to require specific user roles.

    :param required_roles: List of allowed roles
    :return: Decorator function
    """

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            user_role = user.get("role")

            if user_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {required_roles}",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
