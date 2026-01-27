from typing import Optional
from pydantic import BaseModel, Field


# ============ Auth Schemas ============

class RegisterRequest(BaseModel):
    """Request for user registration"""
    device_id: str = Field(..., min_length=1, max_length=255)
    platform: str = Field(default="android", max_length=50)


class LoginRequest(BaseModel):
    """Request for user login"""
    device_id: str = Field(..., min_length=1, max_length=255)


class AuthResponse(BaseModel):
    """Response for auth endpoints"""
    user_id: str
    token: str
    refresh_token: str
    expires_at: Optional[str] = None


# ============ User Schemas ============

class BalanceResponse(BaseModel):
    """Response for balance endpoint"""
    balance: int


# ============ Health Schemas ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    service: str = "dating-coach-api"
