"""
Subscription router for Dating Coach.

Proxies subscription verification to Payment Service.
Status check lives in user.py: GET /v1/user/subscription.
"""
import logging
from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional

from app.client import service_client
from app.schemas import VerifySubscriptionRequest
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


@router.post("/verify")
async def verify_subscription(
    request: VerifySubscriptionRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Verify a subscription purchase.
    Proxies to Payment Service: POST /v1/payment/verify-subscription.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    try:
        data = await service_client.verify_subscription(
            jwt_token=token,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
            platform=request.platform,
            base_plan_id=getattr(request, "base_plan_id", None),
        )
        return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=e.response.json().get("detail", "Verification failed"),
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service unavailable",
        )
