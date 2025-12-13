"""
FastAPI Dependencies for Prescription Service.

This module defines reusable dependencies for authentication and authorization.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from common.auth.jwt_handler import decode_jwt
from config import get_settings


settings = get_settings()
security = HTTPBearer()


async def require_authentication(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to require authentication.

    :param credentials: HTTP Bearer credentials
    :return: Decoded JWT payload
    :raises HTTPException: If token is invalid
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization code",
        )

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

    return payload
