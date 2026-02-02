from fastapi import APIRouter, HTTPException, status
import logging

from app.client import service_client
from app.schemas import AppSettingsResponse

router = APIRouter(prefix="/v1/settings", tags=["settings"])
logger = logging.getLogger(__name__)


@router.get("", response_model=AppSettingsResponse)
async def get_settings() -> AppSettingsResponse:
    """
    Get application settings.
    
    Returns credit costs, bonuses, and packages configuration.
    No authentication required - public endpoint.
    """
    try:
        data = await service_client.get_app_settings()
        return AppSettingsResponse(**data)
        
    except Exception as e:
        logger.error(f"❌ [Settings] Failed to get settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config service unavailable"
        )
