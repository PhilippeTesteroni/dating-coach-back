import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_session
from app.dependencies import get_current_user_id
from app.models import TrainingAttempt, Conversation
from app.services.evaluator import evaluator
from app.services.progress_service import progress_service
from app.schemas import (
    EvaluateRequest, EvaluateResponse, EvaluateFeedback,
    ProgressResponse, TrainingConversationItem, TrainingHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/practice", tags=["practice"])


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_training(
    request: EvaluateRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> EvaluateResponse:
    """
    Evaluate a completed training conversation.

    Called when user taps "Finish" in training mode.
    Returns pass/fail, feedback, and list of newly unlocked levels.
    """
    try:
        conversation_id = UUID(request.conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    try:
        result = await evaluator.evaluate(
            db=session,
            user_id=user_id,
            conversation_id=conversation_id,
            submode_id=request.submode_id,
            difficulty_level=request.difficulty_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ [Practice] evaluate failed: {e}")
        raise HTTPException(status_code=502, detail="Evaluation service unavailable")

    feedback_raw = result.get("feedback", {})
    return EvaluateResponse(
        status=result["status"],
        feedback=EvaluateFeedback(
            observed=feedback_raw.get("observed", []),
            interpretation=feedback_raw.get("interpretation", []),
        ),
        unlocked=result.get("unlocked", []),
    )


@router.get("/progress", response_model=ProgressResponse)
async def get_progress(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProgressResponse:
    """
    Get full training progress for the current user.

    Returns unlock/pass state for all trainings and difficulty levels.
    """
    data = await progress_service.get_progress(db=session, user_id=user_id)

    return ProgressResponse(
        onboarding_complete=data["onboarding_complete"],
        pre_training_conversation_id=data.get("pre_training_conversation_id"),
        trainings=[
            {
                "submode_id": t["submode_id"],
                "levels": t["levels"],
            }
            for t in data["trainings"]
        ],
    )


@router.post("/initialize", status_code=status.HTTP_204_NO_CONTENT)
async def initialize_progress(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Initialize training progress after onboarding completion.

    Idempotent — safe to call multiple times.
    Unlocks: first_contact easy+medium, keep_conversation easy.
    """
    await progress_service.initialize_progress(db=session, user_id=user_id)
    logger.info(f"✅ [Practice] progress initialized for user={user_id}")


@router.get("/history", response_model=TrainingHistoryResponse)
async def get_training_history(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> TrainingHistoryResponse:
    """
    Get training conversation history for the current user.

    Returns all training conversations (excluding pre_training),
    sorted by created_at desc. Includes evaluate result if available.
    """
    # 1. All training conversations (excluding pre_training)
    conv_result = await session.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.mode_id == "training",
            Conversation.submode_id != "pre_training",
        )
        .order_by(Conversation.created_at.desc())
    )
    conversations = conv_result.scalars().all()

    if not conversations:
        return TrainingHistoryResponse(conversations=[])

    # 2. Load all attempts for these conversations in one query
    conv_ids = [c.id for c in conversations]
    attempt_result = await session.execute(
        select(TrainingAttempt).where(TrainingAttempt.conversation_id.in_(conv_ids))
    )
    attempts = attempt_result.scalars().all()

    # Index by conversation_id (one attempt per conversation)
    attempt_index: dict = {a.conversation_id: a for a in attempts}

    # 3. Build response
    items = []
    for c in conversations:
        attempt = attempt_index.get(c.id)
        feedback = None
        if attempt and attempt.feedback:
            try:
                raw = json.loads(attempt.feedback)
                feedback = EvaluateFeedback(
                    observed=raw.get("observed", []),
                    interpretation=raw.get("interpretation", []),
                )
            except Exception:
                pass

        items.append(TrainingConversationItem(
            conversation_id=str(c.id),
            submode_id=c.submode_id,
            difficulty_level=c.difficulty_level,
            created_at=c.created_at.isoformat(),
            attempt_id=str(attempt.id) if attempt else None,
            status=attempt.status if attempt else None,
            feedback=feedback,
        ))

    return TrainingHistoryResponse(conversations=items)


@router.delete("/history/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a training conversation from history.

    Deletes the conversation (cascade deletes messages and attempt).
    """
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await session.commit()
    logger.info(f"🗑 [Practice] conversation={conversation_id} deleted for user={user_id}")
