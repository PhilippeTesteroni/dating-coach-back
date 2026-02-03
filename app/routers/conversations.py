import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.dependencies import get_current_user_id, get_current_user_token
from app.models import Conversation, Message, UserProfile, ActorType, MessageRole
from app.schemas import (
    CreateConversationRequest, ConversationResponse,
    MessageResponse, MessagesResponse,
    SendMessageRequest, SendMessageResponse,
    ConversationListItem, ConversationsListResponse
)
from app.client import service_client
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.get("", response_model=ConversationsListResponse)
async def list_conversations(
    submode_id: str,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> ConversationsListResponse:
    """
    List conversations for a specific submode.
    
    Returns conversations sorted by updated_at DESC with last message preview.
    """
    # Subquery: message count per conversation
    msg_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
        .label("message_count")
    )

    # Subquery: last message content per conversation
    last_msg_subq = (
        select(Message.content)
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .order_by(desc(Message.created_at))
        .limit(1)
        .scalar_subquery()
        .label("last_message")
    )

    # Main query
    result = await session.execute(
        select(
            Conversation,
            last_msg_subq,
            msg_count_subq,
        )
        .where(
            Conversation.user_id == user_id,
            Conversation.submode_id == submode_id,
        )
        .order_by(desc(Conversation.updated_at))
        .limit(50)
    )

    rows = result.all()

    conversations = [
        ConversationListItem(
            id=str(conv.id),
            submode_id=conv.submode_id,
            actor_type=conv.actor_type,
            character_id=conv.character_id,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            last_message=last_message,
            message_count=message_count or 0,
        )
        for conv, last_message, message_count in rows
    ]

    return ConversationsListResponse(conversations=conversations)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> ConversationResponse:
    """
    Create a new conversation.
    
    For character modes: generates model_age, calculates orientation.
    For coach modes: no character params needed.
    """
    # Get user profile
    profile = await session.get(UserProfile, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Create profile first.")
    
    # Get modes to validate and get actor_type
    modes_data = await service_client.get_modes()
    submode = next((m for m in modes_data.get("modes", []) if m["id"] == request.submode_id), None)
    
    if not submode:
        raise HTTPException(status_code=400, detail=f"Invalid submode_id: {request.submode_id}")
    
    # Extract mode_id (category) from submode
    mode_id = submode["category"]
    actor_type = ActorType(submode["actor_type"])
    
    # Validate character_id for character modes
    character_id = None
    model_age = None
    model_orientation = None
    
    if actor_type == ActorType.character:
        if not request.character_id:
            raise HTTPException(status_code=400, detail="character_id required for character modes")
        
        # Validate character exists
        characters_data = await service_client.get_characters()
        character = next(
            (c for c in characters_data.get("characters", []) if c["id"] == request.character_id),
            None
        )
        if not character or character.get("type") == "coach":
            raise HTTPException(status_code=400, detail=f"Invalid character_id: {request.character_id}")
        
        character_id = request.character_id
        model_age = PromptBuilder.generate_model_age(profile.age_range_min, profile.age_range_max)
        model_orientation = PromptBuilder.calculate_orientation(
            profile.gender.value if profile.gender else "male",
            profile.preferred_gender.value
        )
    
    # Create conversation
    conversation = Conversation(
        user_id=user_id,
        mode_id=mode_id,
        submode_id=request.submode_id,
        actor_type=actor_type,
        character_id=character_id,
        model_age=model_age,
        model_orientation=model_orientation,
        language=request.language
    )
    
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    
    logger.info(f"✅ Created conversation {conversation.id} for user {user_id}")
    
    # Generate greeting if scenario requires it
    first_message_response = None
    scenario = await service_client.get_scenario(request.submode_id)
    
    if scenario.get("greeting"):
        try:
            system_prompt = await _build_system_prompt(conversation, profile)
            
            ai_response = await service_client.call_ai(
                messages=[],
                system_prompt=system_prompt
            )
            
            greeting_message = Message(
                conversation_id=conversation.id,
                role=MessageRole.assistant,
                content=ai_response
            )
            session.add(greeting_message)
            await session.commit()
            await session.refresh(greeting_message)
            
            first_message_response = MessageResponse(
                id=str(greeting_message.id),
                role=greeting_message.role,
                content=greeting_message.content,
                created_at=greeting_message.created_at.isoformat()
            )
            
            logger.info(f"✅ Generated greeting for conversation {conversation.id}")
        except Exception as e:
            logger.error(f"⚠️ Greeting generation failed (non-blocking): {e}")
    
    return ConversationResponse(
        id=str(conversation.id),
        mode_id=conversation.mode_id,
        submode_id=conversation.submode_id,
        actor_type=conversation.actor_type,
        character_id=conversation.character_id,
        difficulty_level=conversation.difficulty_level,
        model_age=conversation.model_age,
        language=conversation.language,
        is_active=conversation.is_active,
        created_at=conversation.created_at.isoformat(),
        first_message=first_message_response
    )



@router.get("/{conversation_id}/messages", response_model=MessagesResponse)
async def get_messages(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> MessagesResponse:
    """Get all messages in a conversation."""
    # Verify conversation belongs to user
    conversation = await session.get(Conversation, conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    
    return MessagesResponse(
        messages=[
            MessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                created_at=m.created_at.isoformat()
            )
            for m in messages
        ]
    )



@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    user_id: UUID = Depends(get_current_user_id),
    token: str = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_session)
) -> SendMessageResponse:
    """
    Send a message and get AI response.
    
    1. Saves user message
    2. Builds system prompt
    3. Calls AI Gateway
    4. Saves assistant message
    """
    # Get conversation with user profile
    conversation = await session.get(Conversation, conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.is_active:
        raise HTTPException(status_code=400, detail="Conversation is not active")
    
    # Get user profile
    profile = await session.get(UserProfile, user_id)
    
    # Save user message
    user_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.user,
        content=request.content
    )
    session.add(user_message)
    await session.flush()
    
    # Get message history
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history = result.scalars().all()
    
    # Build messages for AI
    messages = [{"role": m.role.value, "content": m.content} for m in history]
    
    # Build system prompt
    system_prompt = await _build_system_prompt(conversation, profile)
    
    # Call AI Gateway
    try:
        ai_response = await service_client.call_ai(
            messages=messages,
            system_prompt=system_prompt
        )
    except Exception as e:
        logger.error(f"❌ AI Gateway error: {e}")
        raise HTTPException(status_code=502, detail="AI service unavailable")
    
    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation_id,
        role=MessageRole.assistant,
        content=ai_response
    )
    session.add(assistant_message)
    await session.commit()
    
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    
    # Deduct credits after successful AI response
    new_balance = None
    try:
        deduct_result = await service_client.deduct_credits(
            jwt_token=token,
            amount=1,
            reason=f"chat:{conversation.submode_id}"
        )
        if deduct_result.get("success"):
            new_balance = deduct_result.get("new_balance")
        else:
            logger.warning(f"⚠️ Deduct failed: {deduct_result.get('error')}")
    except Exception as e:
        logger.error(f"❌ Deduct error (non-blocking): {e}")
    
    logger.info(f"✅ Message exchange in conversation {conversation_id}")
    
    return SendMessageResponse(
        user_message=MessageResponse(
            id=str(user_message.id),
            role=user_message.role,
            content=user_message.content,
            created_at=user_message.created_at.isoformat()
        ),
        assistant_message=MessageResponse(
            id=str(assistant_message.id),
            role=assistant_message.role,
            content=assistant_message.content,
            created_at=assistant_message.created_at.isoformat()
        ),
        new_balance=new_balance
    )


async def _build_system_prompt(conversation: Conversation, profile: UserProfile) -> str:
    """Build system prompt based on conversation type."""
    # Get scenario by submode_id (e.g., open_chat, first_contact)
    scenario = await service_client.get_scenario(conversation.submode_id)
    
    if conversation.actor_type == ActorType.character:
        # Get character
        characters_data = await service_client.get_characters()
        character = next(
            (c for c in characters_data.get("characters", []) if c["id"] == conversation.character_id),
            None
        )
        
        return await PromptBuilder.build_character_prompt(
            character=character,
            scenario=scenario,
            user_gender=profile.gender.value if profile.gender else "male",
            user_preference=profile.preferred_gender.value,
            model_age=conversation.model_age,
            language=conversation.language
        )
    else:
        # Coach mode - get Hitch
        characters_data = await service_client.get_characters()
        hitch = next(
            (c for c in characters_data.get("characters", []) if c["id"] == "hitch"),
            None
        )
        
        return await PromptBuilder.build_coach_prompt(
            coach_character=hitch,
            scenario=scenario,
            language=conversation.language
        )
