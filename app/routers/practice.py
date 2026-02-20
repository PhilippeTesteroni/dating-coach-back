import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_session
from app.dependencies import get_current_user_id
from app.models import TrainingAttempt
from app.services.evaluator import evaluator
from app.services.progress_service import progress_service
from app.schemas import (
    EvaluateRequest, EvaluateResponse, EvaluateFeedback,
    ProgressResponse, TrainingAttemptItem, TrainingHistoryResponse,
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
    Get training attempt history for the current user.

    Returns all attempts sorted by date descending.
    """
    result = await session.execute(
        select(TrainingAttempt)
        .where(TrainingAttempt.user_id == user_id)
        .order_by(TrainingAttempt.created_at.desc())
    )
    attempts = result.scalars().all()

    items = []
    for a in attempts:
        feedback = None
        if a.feedback:
            try:
                raw = json.loads(a.feedback)
                feedback = EvaluateFeedback(
                    observed=raw.get("observed", []),
                    interpretation=raw.get("interpretation", []),
                )
            except Exception:
                pass

        items.append(TrainingAttemptItem(
            attempt_id=str(a.id),
            conversation_id=str(a.conversation_id) if a.conversation_id else None,
            submode_id=a.submode_id,
            difficulty_level=a.difficulty_level,
            status=a.status.value,  # AttemptStatus.pass_ → "pass", AttemptStatus.fail → "fail"
            created_at=a.created_at.isoformat(),
            feedback=feedback,
        ))

    return TrainingHistoryResponse(attempts=items)


@router.delete("/history/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_attempt(
    attempt_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a training attempt from history.

    Only deletes the attempt record. Conversation is not affected.
    """
    result = await session.execute(
        select(TrainingAttempt).where(
            TrainingAttempt.id == attempt_id,
            TrainingAttempt.user_id == user_id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    await session.execute(
        delete(TrainingAttempt).where(TrainingAttempt.id == attempt_id)
    )
    await session.commit()
    logger.info(f"🗑 [Practice] attempt={attempt_id} deleted for user={user_id}")
