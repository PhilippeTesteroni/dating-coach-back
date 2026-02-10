"""
Subscription router for Dating Coach.

Handles subscription status checks and purchase verification.
Runs in parallel with credits — does NOT touch Payment Service.
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user_id
from app.models import (
    Subscription, MessageCounter, SubscriptionStatus as SubStatus,
)
from app.schemas import (
    SubscriptionStatusResponse,
    SubscriptionStatusEnum,
    VerifySubscriptionRequest,
)
from app.client import service_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/subscription", tags=["subscription"])

# Default free message limit — overridden by S3 app-settings if available
DEFAULT_FREE_MESSAGE_LIMIT = 10


async def _get_free_message_limit() -> int:
    """Get free_message_limit from Config Service, fallback to default."""
    try:
        settings_data = await service_client.get_app_settings()
        return settings_data.get("free_message_limit", DEFAULT_FREE_MESSAGE_LIMIT)
    except Exception:
        return DEFAULT_FREE_MESSAGE_LIMIT


@router.get("", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> SubscriptionStatusResponse:
    """
    Get current subscription status and free-tier usage.

    Returns:
        - subscription_status: none/active/expired/cancelled
        - is_subscribed: True if active subscription
        - messages_used: total messages sent (free-tier counter)
        - free_message_limit: max free messages allowed
        - messages_remaining: None if subscribed (unlimited), else remaining count
    """
    # Get subscription
    sub = await session.get(Subscription, user_id)

    # Check if subscription is active (and not expired)
    is_subscribed = False
    sub_status = SubStatus.none
    expires_at = None
    product_id = None

    if sub:
        # Auto-expire if past expires_at
        if sub.status == SubStatus.active and sub.expires_at and sub.expires_at < datetime.utcnow():
            sub.status = SubStatus.expired
            await session.commit()
            await session.refresh(sub)

        sub_status = sub.status
        is_subscribed = sub.status == SubStatus.active
        expires_at = sub.expires_at.isoformat() if sub.expires_at else None
        product_id = sub.product_id

    # Get message counter
    counter = await session.get(MessageCounter, user_id)
    messages_used = counter.message_count if counter else 0

    # Get limit from config
    free_limit = await _get_free_message_limit()

    # Calculate remaining
    if is_subscribed:
        messages_remaining = None  # unlimited
    else:
        messages_remaining = max(0, free_limit - messages_used)

    return SubscriptionStatusResponse(
        subscription_status=SubscriptionStatusEnum(sub_status.value),
        is_subscribed=is_subscribed,
        messages_used=messages_used,
        free_message_limit=free_limit,
        messages_remaining=messages_remaining,
        expires_at=expires_at,
        product_id=product_id,
    )


@router.post("/verify")
async def verify_subscription(
    request: VerifySubscriptionRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Verify a subscription purchase from Google Play / App Store.

    For now: trust the client and activate subscription.
    TODO: Server-side receipt validation via Google Play Developer API / App Store Server API.
    """
    # Get or create subscription record
    sub = await session.get(Subscription, user_id)

    if not sub:
        sub = Subscription(user_id=user_id)
        session.add(sub)

    sub.status = SubStatus.active
    sub.platform = request.platform
    sub.product_id = request.product_id
    sub.purchase_token = request.purchase_token
    sub.expires_at = None  # TODO: set from receipt validation
    sub.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(sub)

    logger.info(f"✅ Subscription activated for user {user_id}, product={request.product_id}")

    return {
        "success": True,
        "subscription_status": "active",
        "product_id": request.product_id,
    }
