import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.client import service_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/modes", tags=["modes"])


class Category(BaseModel):
    id: str
    name: str
    name_ru: str
    order: int


class Mode(BaseModel):
    id: str
    category: str
    name: str
    name_ru: str
    description: str
    actor_type: str
    has_difficulty: bool
    order: int


class ModesResponse(BaseModel):
    categories: List[Category]
    modes: List[Mode]


@router.get("", response_model=ModesResponse)
async def get_modes() -> ModesResponse:
    """
    Get available modes grouped by categories.
    
    Returns all training modes, analysis modes, reflection modes, etc.
    """
    try:
        data = await service_client.get_modes()
        
        categories = [Category(**c) for c in data.get("categories", [])]
        modes = [Mode(**m) for m in data.get("modes", [])]
        
        logger.info(f"✅ Modes loaded: {len(categories)} categories, {len(modes)} modes")
        
        return ModesResponse(categories=categories, modes=modes)
        
    except Exception as e:
        logger.error(f"❌ Failed to get modes: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch modes from config service"
        )
