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
    # Credit-based (legacy, kept for backward compatibility)
    welcome_bonus: Optional[int] = None
    credit_cost: Optional[int] = None
    referrer_bonus: int = 0
    referred_bonus: int = 0
    credit_packages: Optional[List[CreditPackage]] = None
    # Subscription-based (new)
    free_message_limit: Optional[int] = None
    subscription_products: Optional[list] = None


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


class GreetingRequest(BaseModel):
    """Request to generate a greeting without creating a conversation"""
    submode_id: str = Field(..., description="Submode identifier")
    character_id: Optional[str] = Field(None, description="Character ID (for character modes)")
    language: str = Field(default="en", max_length=10)


class GreetingResponse(BaseModel):
    """Generated greeting message"""
    content: str


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    submode_id: str = Field(..., description="Submode identifier (e.g., open_chat, first_contact)")
    character_id: Optional[str] = Field(None, description="Character ID (required for character modes)")
    difficulty_level: Optional[int] = Field(None, ge=1, le=3, description="1=easy, 2=medium, 3=hard (training modes only)")
    language: str = Field(default="ru", max_length=10)
    seed_message: Optional[str] = Field(None, description="Greeting message to save as first assistant message")


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


# ============ Conversation List Schemas ============

class ConversationListItem(BaseModel):
    """Conversation preview for history list"""
    id: str
    submode_id: str
    actor_type: ActorType
    character_id: Optional[str] = None
    created_at: str
    updated_at: str
    last_message: Optional[str] = None
    message_count: int = 0


class ConversationsListResponse(BaseModel):
    """List of conversations for history screen"""
    conversations: List[ConversationListItem]


# ============ Subscription Schemas ============

class SubscriptionStatusEnum(str, Enum):
    none = "none"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class SubscriptionStatusResponse(BaseModel):
    """Current subscription and free-tier status"""
    subscription_status: SubscriptionStatusEnum = SubscriptionStatusEnum.none
    is_subscribed: bool = False
    messages_used: int = 0
    free_message_limit: int = 10
    messages_remaining: Optional[int] = None  # None = unlimited (subscribed)
    expires_at: Optional[str] = None
    product_id: Optional[str] = None


class VerifySubscriptionRequest(BaseModel):
    """Request to verify a subscription purchase"""
    product_id: str = Field(..., description="Subscription product ID (e.g. week_subscription)")
    purchase_token: str = Field(..., description="Store purchase token")
    platform: str = Field(default="google_play", description="google_play or app_store")
    base_plan_id: Optional[str] = Field(None, description="Base plan ID (e.g. 01, 02)")


# ============ Practice Schemas ============

class EvaluateRequest(BaseModel):
    """Request to evaluate a completed training conversation"""
    conversation_id: str = Field(..., description="UUID of the training conversation")
    submode_id: str = Field(..., description="Training submode (e.g. first_contact)")
    difficulty_level: int = Field(..., ge=1, le=3, description="1=easy, 2=medium, 3=hard")


class EvaluateFeedback(BaseModel):
    observed: List[str]
    interpretation: List[str]


class EvaluateResponse(BaseModel):
    """Result of training evaluation"""
    status: str                          # "pass" | "fail"
    feedback: EvaluateFeedback
    unlocked: List[dict]                 # [{submode_id, difficulty_level}, ...]


class TrainingLevelState(BaseModel):
    difficulty_level: int
    is_unlocked: bool
    passed: bool
    passed_at: Optional[str] = None


class TrainingState(BaseModel):
    submode_id: str
    levels: List[TrainingLevelState]


class ProgressResponse(BaseModel):
    """Full training progress for the user"""
    onboarding_complete: bool
    pre_training_conversation_id: Optional[str] = None
    trainings: List[TrainingState]


class TrainingConversationItem(BaseModel):
    """Single training conversation for history list.
    
    conversation_id — для открытия чата.
    attempt_id / status / feedback — если evaluate был пройден.
    """
    conversation_id: str
    submode_id: str
    difficulty_level: Optional[int] = None
    created_at: str
    # Результат evaluate (null если ещё не оценён)
    attempt_id: Optional[str] = None
    status: Optional[str] = None         # "pass" | "fail" | null
    feedback: Optional[EvaluateFeedback] = None


class TrainingHistoryResponse(BaseModel):
    """List of training conversations for history screen"""
    conversations: List[TrainingConversationItem]
