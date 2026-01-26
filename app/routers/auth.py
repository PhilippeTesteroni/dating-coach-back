from fastapi import APIRouter, HTTPException, status
import httpx

from app.client import service_client
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest) -> AuthResponse:
    """
    Register new user (or get existing by device_id).
    
    Called on first app launch. Creates user if device_id is new,
    otherwise returns existing user's tokens.
    
    Flow:
    1. App sends device_id + platform
    2. dating-coach-api proxies to Identity Service
    3. Identity resolves/creates user, returns JWT tokens
    4. App stores tokens for future requests
    """
    try:
        data = await service_client.get_auth_token(
            device_id=request.device_id,
            platform=request.platform,
        )
        
        return AuthResponse(
            user_id=data["user_id"],
            token=data["access_token"],
            refresh_token=data["refresh_token"],
        )
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Authentication failed"
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity service unavailable"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    """
    Login existing user by device_id.
    
    Called on subsequent app launches.
    Semantically same as register - Identity Service handles both cases.
    """
    try:
        data = await service_client.get_auth_token(
            device_id=request.device_id,
            platform="device",  # Generic platform for login
        )
        
        return AuthResponse(
            user_id=data["user_id"],
            token=data["access_token"],
            refresh_token=data["refresh_token"],
        )
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Login failed"
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity service unavailable"
        )
