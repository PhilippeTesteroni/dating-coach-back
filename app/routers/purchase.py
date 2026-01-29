from fastapi import APIRouter, Depends, HTTPException, status
import httpx
import logging

from app.schemas import VerifyPurchaseRequest, VerifyPurchaseResponse
from app.dependencies import get_current_user_token
from app.client import service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/purchase", tags=["purchase"])


@router.post("/verify", response_model=VerifyPurchaseResponse)
async def verify_purchase(
    request: VerifyPurchaseRequest,
    token: str = Depends(get_current_user_token)
) -> VerifyPurchaseResponse:
    """
    Verify a Google Play purchase and add credits.
    
    Proxies to Payment Service which:
    - Checks purchase_token uniqueness (replay protection)
    - Maps product_id to credits
    - Updates user balance
    """
    try:
        result = await service_client.verify_purchase(
            jwt_token=token,
            product_id=request.product_id,
            purchase_token=request.purchase_token,
            platform=request.platform
        )
        
        return VerifyPurchaseResponse(
            success=result.get("success", False),
            credits_added=result.get("credits_added", 0),
            new_balance=result.get("new_balance", 0)
        )
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Purchase already processed"
            )
        logger.error(f"Payment service error: {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment service error"
        )
    except Exception as e:
        logger.error(f"Verify purchase failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify purchase"
        )
