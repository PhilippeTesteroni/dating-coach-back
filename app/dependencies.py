from fastapi import Header, HTTPException, status
from typing import Optional
from uuid import UUID
import jwt

from app.config import settings


async def get_current_user_id(
    authorization: Optional[str] = Header(None)
) -> UUID:
    """
    Extract user_id from JWT token in Authorization header.
    
    Raises:
        401: If token is missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        return UUID(user_id)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user_token(
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Extract raw JWT token from Authorization header.
    Used for proxying to other services.
    
    Raises:
        401: If token is missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    return authorization.replace("Bearer ", "")
