"""Standardized API response utilities."""
from typing import Optional, Any, Dict
from fastapi.responses import JSONResponse
from fastapi import status
from datetime import datetime
import uuid


class APIResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        correlation_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """Create a successful API response."""
        response_data = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4())
        }
        if meta:
            response_data["meta"] = meta
        return JSONResponse(status_code=status_code, content=response_data)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> JSONResponse:
        """Create an error API response."""
        response_data = {
            "success": False,
            "message": message,
            "error": {
                "code": error_code or f"ERR_{status_code}",
                "message": message,
                "details": details or {}
            },
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id or str(uuid.uuid4())
        }
        return JSONResponse(status_code=status_code, content=response_data)

