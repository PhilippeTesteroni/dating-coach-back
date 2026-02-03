from typing import Optional, List
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
    platform: str = Field(default="android", max_length=50)


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


# ============ Purchase Schemas ============

class VerifyPurchaseRequest(BaseModel):
    """Request to verify a purchase"""
    product_id: str = Field(..., description="Google Play product ID (e.g. credits_10)")
    purchase_token: str = Field(..., description="Google Play purchase token")
    platform: str = Field(default="google_play", description="Platform identifier")


class VerifyPurchaseResponse(BaseModel):
    """Response from purchase verification"""
    success: bool
    credits_added: int
    new_balance: int


# ============ App Settings Schemas ============

class CreditPackage(BaseModel):
    """Credit package for purchase"""
    product_id: str
    credits: int
    price: float
    currency: str = "USD"


class AppSettingsResponse(BaseModel):
    """Application settings from Config Service"""
    app_id: str
    welcome_bonus: int
    credit_cost: int
    referrer_bonus: int
    referred_bonus: int
    credit_packages: Optional[List[CreditPackage]] = None


# ============ Character Schemas ============

class CharacterType(str, Enum):
    coach = "coach"
    character = "character"


class Character(BaseModel):
    """Character data for selection screen"""
    id: str
    type: CharacterType
    name: str
    description: str
    gender: Optional[str] = None
    avatar_url: str
    thumb_url: str


class CharactersResponse(BaseModel):
    """Response with filtered characters list"""
    characters: List[Character]


# ============ Conversation Schemas ============

class ActorType(str, Enum):
    character = "character"
    coach = "coach"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    submode_id: str = Field(..., description="Submode identifier (e.g., open_chat, first_contact)")
    character_id: Optional[str] = Field(None, description="Character ID (required for character modes)")
    language: str = Field(default="ru", max_length=10)


class ConversationResponse(BaseModel):
    """Conversation data"""
    id: str
    mode_id: str  # category: training, analysis, reflection, free_practice
    submode_id: str  # specific mode: open_chat, first_contact, etc.
    actor_type: ActorType
    character_id: Optional[str] = None
    difficulty_level: Optional[int] = None
    model_age: Optional[int] = None
    language: str
    is_active: bool
    created_at: str
    first_message: Optional['MessageResponse'] = None


class MessageResponse(BaseModel):
    """Single message"""
    id: str
    role: MessageRole
    content: str
    created_at: str


class MessagesResponse(BaseModel):
    """List of messages"""
    messages: List[MessageResponse]


class SendMessageRequest(BaseModel):
    """Request to send a message"""
    content: str = Field(..., min_length=1, max_length=4000)


class SendMessageResponse(BaseModel):
    """Response after sending message"""
    user_message: MessageResponse
    assistant_message: MessageResponse
    new_balance: Optional[int] = None
