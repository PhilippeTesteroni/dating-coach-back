"""
Subscription router for Dating Coach.

Handles subscription purchase verification.
Status check lives in user.py: GET /v1/user/subscription.
"""
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user_id
from app.models import Subscription, SubscriptionStatus as SubStatus
from app.schemas import VerifySubscriptionRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


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
