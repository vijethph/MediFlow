"""Common authentication utilities."""

from common.auth.jwt_handler import (
    JWTBearer,
    create_access_token,
    decode_jwt,
    get_current_user,
    require_role,
)

__all__ = [
    "JWTBearer",
    "create_access_token",
    "decode_jwt",
    "get_current_user",
    "require_role",
]
