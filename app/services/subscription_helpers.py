"""
Subscription helpers shared across routers.

Subscription state lives in Payment Service.
Free-tier counters (MessageCounter) stay local in dating-coach-back.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.client import service_client
from app.models import MessageCounter
from app.schemas import SubscriptionStatusResponse, SubscriptionStatusEnum

logger = logging.getLogger(__name__)
DEFAULT_FREE_MESSAGE_LIMIT = 30


async def get_free_message_limit() -> int:
    """Get free_message_limit from Config Service, fallback to default."""
    try:
        settings_data = await service_client.get_app_settings()
        return settings_data.get("free_message_limit", DEFAULT_FREE_MESSAGE_LIMIT)
    except Exception:
        return DEFAULT_FREE_MESSAGE_LIMIT


async def check_subscription_via_payment(jwt_token: str) -> bool:
    """
    Check if user has active subscription via Payment Service.
    Returns True if subscribed, False otherwise.
    Swallows errors → treats as not subscribed.
    """
    try:
        data = await service_client.get_subscription_status(jwt_token)
        return data.get("is_subscribed", False)
    except Exception as e:
        logger.warning(f"⚠️ Payment Service subscription check failed: {e}")
        return False


async def build_subscription_status(
    user_id: UUID,
    jwt_token: str,
    session: AsyncSession,
) -> SubscriptionStatusResponse:
    """
    Build subscription status response for a user.
    Combines Payment Service (subscription) + local DB (message counter).
    """
    # Get subscription state from Payment Service
    is_subscribed = False
    sub_status = SubscriptionStatusEnum.none
    expires_at = None
    product_id = None

    try:
        data = await service_client.get_subscription_status(jwt_token)
        is_subscribed = data.get("is_subscribed", False)
        raw_status = data.get("subscription_status")
        if raw_status:
            try:
                sub_status = SubscriptionStatusEnum(raw_status)
            except ValueError:
                sub_status = SubscriptionStatusEnum.none
        expires_at = data.get("expires_at")
        product_id = data.get("product_id")
    except Exception as e:
        logger.warning(f"⚠️ Payment Service unavailable: {e}")

    # Local: message counter
    counter = await session.get(MessageCounter, user_id)
    messages_used = counter.message_count if counter else 0

    free_limit = await get_free_message_limit()

    messages_remaining = None if is_subscribed else max(0, free_limit - messages_used)

    return SubscriptionStatusResponse(
        subscription_status=sub_status,
        is_subscribed=is_subscribed,
        messages_used=messages_used,
        free_message_limit=free_limit,
        messages_remaining=messages_remaining,
        expires_at=expires_at,
        product_id=product_id,
    )
