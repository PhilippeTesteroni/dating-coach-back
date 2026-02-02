import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, status

from app.client import service_client
from app.schemas import Character, CharactersResponse, CharacterType, PreferredGender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/characters", tags=["characters"])


@router.get("", response_model=CharactersResponse)
async def get_characters(
    preferred_gender: PreferredGender = Query(
        PreferredGender.all,
        description="Filter characters by user's preferred gender"
    )
) -> CharactersResponse:
    """
    Get available characters for selection.
    
    Filtering logic:
    - preferred_gender=female → Hitch (coach) + female characters
    - preferred_gender=male → Hitch (coach) + male characters  
    - preferred_gender=all → All characters
    
    Returns characters without base_prompt (frontend doesn't need it).
    """
    try:
        # Get characters from Config Service
        data = await service_client.get_characters()
        
        all_characters = data.get("characters", [])
        
        # Filter characters based on preferred_gender
        filtered = []
        for char in all_characters:
            available_for = char.get("available_for", [])
            
            # Check if character is available for this preference
            if preferred_gender.value in available_for:
                # Build response without base_prompt
                filtered.append(Character(
                    id=char["id"],
                    type=CharacterType(char["type"]),
                    name=char["name"],
                    description=char["description"],
                    gender=char.get("gender"),
                    avatar_url=char["avatar_url"],
                    thumb_url=char["thumb_url"]
                ))
        
        logger.info(f"✅ Characters filtered: {len(filtered)}/{len(all_characters)} for preferred_gender={preferred_gender.value}")
        
        return CharactersResponse(characters=filtered)
        
    except Exception as e:
        logger.error(f"❌ Failed to get characters: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch characters from config service"
        )
