from fastapi import APIRouter, HTTPException, status, Header
import httpx
import logging
from typing import Optional

from app.client import service_client
from app.schemas import BalanceResponse

router = APIRouter(prefix="/v1/user", tags=["user"])
logger = logging.getLogger(__name__)


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    authorization: Optional[str] = Header(None)
) -> BalanceResponse:
    """
    Get user's credit balance.
    
    Requires JWT token in Authorization header.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        data = await service_client.check_balance(jwt_token=token)
        
        return BalanceResponse(
            balance=data.get("balance", 0)
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ [Balance] HTTP {e.response.status_code}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail="Failed to get balance"
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service unavailable"
        )
