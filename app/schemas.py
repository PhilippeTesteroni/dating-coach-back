from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


# ============ Enums ============

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class PreferredGender(str, Enum):
    all = "all"
    male = "male"
    female = "female"


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


class ProfileResponse(BaseModel):
    """User profile data"""
    user_id: str
    name: Optional[str] = None
    gender: Optional[Gender] = None
    preferred_gender: PreferredGender = PreferredGender.all
    age_range_min: int = 18
    age_range_max: int = 99
    avatar_url: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    """Request to update profile"""
    name: Optional[str] = Field(None, max_length=100)
    gender: Optional[Gender] = None
    preferred_gender: Optional[PreferredGender] = None
    age_range_min: Optional[int] = Field(None, ge=18, le=99)
    age_range_max: Optional[int] = Field(None, ge=18, le=99)
    avatar_url: Optional[str] = Field(None, max_length=500)


class AvatarUploadUrlResponse(BaseModel):
    """Presigned URL for avatar upload"""
    upload_url: str
    avatar_url: str  # Final URL after upload


# ============ Health Schemas ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "ok"
    service: str = "dating-coach-api"
