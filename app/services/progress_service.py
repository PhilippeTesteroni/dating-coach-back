import logging
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.models import TrainingProgress

logger = logging.getLogger(__name__)

# All trainings in campaign order
TRAINING_ORDER = [
    "first_contact",
    "keep_conversation",
    "losing_interest",
    "rejections",
    "ask_for_date",
    "intimacy_boundaries",
    "after_date",
]

DIFFICULTY_LEVELS = [1, 2, 3]  # 1=easy, 2=medium, 3=hard


class ProgressService:
    """
    Manages training progress state for a user.

    Rules:
    - initialize_progress(): called after pre-training onboarding
      → unlocks first_contact easy(1) + medium(2), keep_conversation easy(1)
    - unlock_next(): called by Evaluator on pass, applies campaign unlock rules
    - get_progress(): returns full state for all trainings
    """

    async def initialize_progress(self, db: AsyncSession, user_id: UUID) -> None:
        """
        Set initial unlocked state after onboarding.

        Unlocks:
        - first_contact: easy(1), medium(2)
        - keep_conversation: easy(1)
        """
        # Wipe any existing progress (idempotent re-init)
        await db.execute(
            delete(TrainingProgress).where(TrainingProgress.user_id == user_id)
        )

        initial_unlocks = [
            ("first_contact", 1),
            ("first_contact", 2),
            ("keep_conversation", 1),
        ]

        for submode_id, level in initial_unlocks:
            db.add(TrainingProgress(
                user_id=user_id,
                submode_id=submode_id,
                difficulty_level=level,
                is_unlocked=True,
                passed=False,
            ))

        await db.commit()
        logger.info(f"✅ [Progress] initialized for user={user_id}")

    async def get_progress(self, db: AsyncSession, user_id: UUID) -> dict:
        """
        Return full progress state.

        Returns:
            {
                onboarding_complete: bool,
                trainings: [
                    {
                        submode_id: str,
                        levels: [
                            {difficulty_level: int, is_unlocked: bool, passed: bool, passed_at: str|null},
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        result = await db.execute(
            select(TrainingProgress).where(TrainingProgress.user_id == user_id)
        )
        rows = result.scalars().all()

        # Index by (submode_id, difficulty_level)
        index: dict[tuple, TrainingProgress] = {
            (r.submode_id, r.difficulty_level): r for r in rows
        }

        onboarding_complete = len(rows) > 0

        trainings = []
        for submode_id in TRAINING_ORDER:
            levels = []
            for level in DIFFICULTY_LEVELS:
                row = index.get((submode_id, level))
                levels.append({
                    "difficulty_level": level,
                    "is_unlocked": row.is_unlocked if row else False,
                    "passed": row.passed if row else False,
                    "passed_at": row.passed_at.isoformat() if (row and row.passed_at) else None,
                })
            trainings.append({"submode_id": submode_id, "levels": levels})

        return {"onboarding_complete": onboarding_complete, "trainings": trainings}

    async def unlock_next(
        self,
        db: AsyncSession,
        user_id: UUID,
        submode_id: str,
        difficulty_level: int,
    ) -> list[dict]:
        """
        Apply unlock rules after passing a level.
        Called by Evaluator — no commit here, Evaluator owns the transaction.

        Returns list of newly unlocked {submode_id, difficulty_level}.
        """
        unlocked = []

        if difficulty_level == 1:
            # easy pass → unlock medium of same
            if await self._unlock(db, user_id, submode_id, 2):
                unlocked.append({"submode_id": submode_id, "difficulty_level": 2})

        elif difficulty_level == 2:
            # medium pass → unlock hard of same + easy of next training
            if await self._unlock(db, user_id, submode_id, 3):
                unlocked.append({"submode_id": submode_id, "difficulty_level": 3})

            next_sub = self._next_submode(submode_id)
            if next_sub:
                if await self._unlock(db, user_id, next_sub, 1):
                    unlocked.append({"submode_id": next_sub, "difficulty_level": 1})

        # hard pass → no new unlocks

        return unlocked

    async def _unlock(
        self, db: AsyncSession, user_id: UUID, submode_id: str, level: int
    ) -> bool:
        """
        Mark a level as unlocked. Returns True if state changed.
        """
        result = await db.execute(
            select(TrainingProgress).where(
                TrainingProgress.user_id == user_id,
                TrainingProgress.submode_id == submode_id,
                TrainingProgress.difficulty_level == level,
            )
        )
        row = result.scalar_one_or_none()

        if not row:
            db.add(TrainingProgress(
                user_id=user_id,
                submode_id=submode_id,
                difficulty_level=level,
                is_unlocked=True,
                passed=False,
            ))
            return True

        if not row.is_unlocked:
            row.is_unlocked = True
            return True

        return False  # Already unlocked

    def _next_submode(self, submode_id: str) -> Optional[str]:
        try:
            idx = TRAINING_ORDER.index(submode_id)
            return TRAINING_ORDER[idx + 1] if idx + 1 < len(TRAINING_ORDER) else None
        except ValueError:
            return None


progress_service = ProgressService()
