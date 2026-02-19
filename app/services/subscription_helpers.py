"""
Subscription helpers shared across routers.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.client import service_client
from app.models import Subscription, MessageCounter, SubscriptionStatus as SubStatus
from app.schemas import SubscriptionStatusResponse, SubscriptionStatusEnum

DEFAULT_FREE_MESSAGE_LIMIT = 10


async def get_free_message_limit() -> int:
    """Get free_message_limit from Config Service, fallback to default."""
    try:
        settings_data = await service_client.get_app_settings()
        return settings_data.get("free_message_limit", DEFAULT_FREE_MESSAGE_LIMIT)
    except Exception:
        return DEFAULT_FREE_MESSAGE_LIMIT


async def build_subscription_status(
    user_id: UUID,
    session: AsyncSession,
) -> SubscriptionStatusResponse:
    """
    Build subscription status response for a user.
    Single source of truth — used by GET /v1/user/subscription.
    """
    sub = await session.get(Subscription, user_id)

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

    counter = await session.get(MessageCounter, user_id)
    messages_used = counter.message_count if counter else 0

    free_limit = await get_free_message_limit()

    if is_subscribed:
        messages_remaining = None
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
