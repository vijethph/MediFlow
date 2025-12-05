"""JWT token validation dependency for FastAPI."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.auth_handler import verify_token
from schemas import TokenData

security = HTTPBearer()


async def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to validate JWT token and extract patient information.
    
    Args:
        credentials: HTTP authorization credentials from header
        
    Returns:
        TokenData with patient_id and email
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = credentials.credentials
    token_data = verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data

