import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user_id
from app.services.evaluator import evaluator
from app.services.progress_service import progress_service
from app.schemas import EvaluateRequest, EvaluateResponse, EvaluateFeedback, ProgressResponse

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
