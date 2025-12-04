"""
FastAPI Dependencies.

This module defines reusable dependencies for authentication and authorization.
"""

from typing import Any, Dict

from fastapi import Depends, Request

from common.auth.jwt_handler import JWTBearer, get_current_user
from config import get_settings


settings = get_settings()


def get_current_user_from_request(request: Request) -> Dict[str, Any]:
    """
    Dependency to get current user from request.

    :param request: FastAPI request object
    :return: User payload from JWT token
    """
    return get_current_user(request)


def require_authentication():
    """
    Dependency to require authentication.

    :return: JWTBearer dependency
    """
    return Depends(JWTBearer())

