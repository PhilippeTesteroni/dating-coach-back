import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.client import service_client
from app.models import TrainingAttempt, TrainingProgress, AttemptStatus, Conversation, Message

logger = logging.getLogger(__name__)

DIFFICULTY_NAMES = {1: "Easy", 2: "Medium", 3: "Hard"}

# Unlock rules per difficulty after PASS:
# pass easy(1)   → unlock medium(2) of same submode
# pass medium(2) → unlock hard(3) of same submode + easy(1) of next submode
# pass hard(3)   → nothing new (optional challenge)
TRAINING_ORDER = [
    "first_contact",
    "keep_conversation",
    "losing_interest",
    "rejections",
    "ask_for_date",
    "intimacy_boundaries",
    "after_date",
]


class Evaluator:
    """
    LLM-based evaluator for training attempts.

    Loads prompts from S3 via Config Service.
    Saves attempt + updates progress in DB.
    """

    async def evaluate(
        self,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: UUID,
        submode_id: str,
        difficulty_level: int,
    ) -> dict:
        """
        Evaluate a completed training conversation.

        Returns:
            {
                status: "pass" | "fail",
                feedback: {observed: [...], interpretation: [...]},
                unlocked: [{submode_id, difficulty_level}, ...]
            }
        """
        # 1. Load conversation messages
        messages = await self._load_messages(db, conversation_id)
        if not messages:
            raise ValueError(f"No messages found for conversation {conversation_id}")

        # 2. Load evaluator prompt from S3
        prompt_data = await service_client.get_file("prompts/training_evaluator.json")
        prompt_config = prompt_data.get("content", {})
        system_prompt = prompt_config.get("system_prompt", "")
        difficulty_name = DIFFICULTY_NAMES.get(difficulty_level, "Medium")

        # 3. Build conversation transcript
        transcript = self._build_transcript(messages)

        # 4. Build user message for evaluator
        user_message = (
            f"Training: {submode_id}\n"
            f"Difficulty: {difficulty_name}\n\n"
            f"Conversation transcript:\n{transcript}\n\n"
            "Evaluate and return JSON only."
        )

        # 5. Call LLM
        logger.info(f"🚀 [Evaluator] evaluate conv={conversation_id} submode={submode_id} level={difficulty_level}")
        raw_response = await service_client.call_ai(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=0.2,
        )

        # 6. Parse response
        result = self._parse_response(raw_response)
        status = result.get("status", "fail")
        feedback = result.get("feedback", {"observed": [], "interpretation": []})

        # 7. Save attempt
        attempt = TrainingAttempt(
            user_id=user_id,
            conversation_id=conversation_id,
            submode_id=submode_id,
            difficulty_level=difficulty_level,
            status=AttemptStatus.pass_ if status == "pass" else AttemptStatus.fail,
            feedback=json.dumps(feedback),
        )
        db.add(attempt)

        # 8. Update progress + unlock next levels on pass
        unlocked = []
        if status == "pass":
            unlocked = await self._handle_pass(db, user_id, submode_id, difficulty_level)

        await db.commit()

        logger.info(f"✅ [Evaluator] status={status}, unlocked={unlocked}")
        return {"status": status, "feedback": feedback, "unlocked": unlocked}

    async def _load_messages(self, db: AsyncSession, conversation_id: UUID) -> list:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return result.scalars().all()

    def _build_transcript(self, messages: list) -> str:
        lines = []
        for m in messages:
            role = "User" if m.role.value == "user" else "Character"
            lines.append(f"{role}: {m.content}")
        return "\n".join(lines)

    def _parse_response(self, raw: str) -> dict:
        try:
            # Strip markdown fences if present
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except Exception as e:
            logger.error(f"❌ [Evaluator] Failed to parse response: {e}\nRaw: {raw[:200]}")
            return {"status": "fail", "feedback": {"observed": [], "interpretation": []}}

    async def _handle_pass(
        self, db: AsyncSession, user_id: UUID, submode_id: str, difficulty_level: int
    ) -> list:
        """Mark current level passed, unlock next levels per campaign rules."""
        unlocked = []

        # Mark passed
        await self._set_passed(db, user_id, submode_id, difficulty_level)

        if difficulty_level == 1:  # easy → unlock medium of same
            await self._unlock(db, user_id, submode_id, 2)
            unlocked.append({"submode_id": submode_id, "difficulty_level": 2})

        elif difficulty_level == 2:  # medium → unlock hard of same + easy of next
            await self._unlock(db, user_id, submode_id, 3)
            unlocked.append({"submode_id": submode_id, "difficulty_level": 3})

            next_submode = self._next_submode(submode_id)
            if next_submode:
                await self._unlock(db, user_id, next_submode, 1)
                unlocked.append({"submode_id": next_submode, "difficulty_level": 1})

        # hard pass → nothing new

        return unlocked

    async def _set_passed(self, db: AsyncSession, user_id: UUID, submode_id: str, level: int):
        result = await db.execute(
            select(TrainingProgress).where(
                TrainingProgress.user_id == user_id,
                TrainingProgress.submode_id == submode_id,
                TrainingProgress.difficulty_level == level,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            row.passed = True
            row.passed_at = datetime.utcnow()
        else:
            db.add(TrainingProgress(
                user_id=user_id, submode_id=submode_id,
                difficulty_level=level, is_unlocked=True,
                passed=True, passed_at=datetime.utcnow(),
            ))

    async def _unlock(self, db: AsyncSession, user_id: UUID, submode_id: str, level: int):
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
                user_id=user_id, submode_id=submode_id,
                difficulty_level=level, is_unlocked=True, passed=False,
            ))
        elif not row.is_unlocked:
            row.is_unlocked = True

    def _next_submode(self, submode_id: str) -> Optional[str]:
        try:
            idx = TRAINING_ORDER.index(submode_id)
            return TRAINING_ORDER[idx + 1] if idx + 1 < len(TRAINING_ORDER) else None
        except ValueError:
            return None


evaluator = Evaluator()
