from fastapi import APIRouter, HTTPException, status, Header, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import logging
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.models import UserProfile
from app.client import service_client
from app.s3_client import s3_client
from app.schemas import (
    BalanceResponse, 
    ProfileResponse, 
    ProfileUpdateRequest,
    AvatarUploadUrlResponse
)
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/v1/user", tags=["user"])
logger = logging.getLogger(__name__)


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    authorization: Optional[str] = Header(None)
) -> BalanceResponse:
    """Get user's credit balance."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        data = await service_client.check_balance(jwt_token=token)
        return BalanceResponse(balance=data.get("balance", 0))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Failed to get balance")
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """Get user profile."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Return empty profile for new users
        return ProfileResponse(user_id=str(user_id))
    
    return ProfileResponse(
        user_id=str(profile.user_id),
        name=profile.name,
        gender=profile.gender,
        preferred_gender=profile.preferred_gender,
        age_range_min=profile.age_range_min,
        age_range_max=profile.age_range_max,
        avatar_url=profile.avatar_url,
    )


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """Update user profile."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        # Create new profile
        profile = UserProfile(user_id=user_id)
        db.add(profile)
    
    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return ProfileResponse(
        user_id=str(profile.user_id),
        name=profile.name,
        gender=profile.gender,
        preferred_gender=profile.preferred_gender,
        age_range_min=profile.age_range_min,
        age_range_max=profile.age_range_max,
        avatar_url=profile.avatar_url,
    )


@router.post("/avatar/upload-url", response_model=AvatarUploadUrlResponse)
async def get_avatar_upload_url(
    user_id: UUID = Depends(get_current_user_id)
) -> AvatarUploadUrlResponse:
    """
    Get presigned URL for avatar upload.
    
    Returns URL for direct PUT to S3.
    After upload, call PATCH /profile with avatar_url.
    """
    upload_url = s3_client.generate_presigned_upload_url(user_id)
    avatar_url = s3_client.get_avatar_url(user_id)
    
    return AvatarUploadUrlResponse(
        upload_url=upload_url,
        avatar_url=avatar_url
    )


@router.delete("/{user_id}")
async def delete_user_data(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete user data from Dating Coach.
    Called by Identity Service during cascade deletion.
    
    Cascade chain (all via DB ON DELETE CASCADE):
      dc_user_profiles → dc_conversations → dc_messages
    """
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if profile:
        await db.delete(profile)
        await db.commit()
        logger.info(f"✅ Deleted user {user_id}: profile + conversations + messages (cascade)")
    
    return {"success": True, "message": "User data deleted"}
