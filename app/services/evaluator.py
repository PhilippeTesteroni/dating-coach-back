import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.client import service_client
from app.models import TrainingAttempt, TrainingProgress, Message
from app.services.progress_service import progress_service

logger = logging.getLogger(__name__)

DIFFICULTY_NAMES = {1: "Easy", 2: "Medium", 3: "Hard"}


class Evaluator:
    """
    LLM-based evaluator for training attempts.

    Loads system prompt from S3 via Config Service.
    Delegates unlock logic to ProgressService.
    Owns the DB transaction (commit after attempt + progress updates).
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
        # 1. Load messages
        messages = await self._load_messages(db, conversation_id)
        if not messages:
            raise ValueError(f"No messages found for conversation {conversation_id}")

        # 2. Load evaluator prompt from S3
        prompt_data = await service_client.get_file("prompts/training_evaluator.json")
        # FileResponse wraps content in "content" field
        system_prompt = prompt_data.get("content", {}).get("system_prompt", "")

        # 3. Build user message
        transcript = self._build_transcript(messages)
        user_message = (
            f"Training: {submode_id}\n"
            f"Difficulty: {DIFFICULTY_NAMES.get(difficulty_level, 'Medium')}\n\n"
            f"Conversation transcript:\n{transcript}\n\n"
            "Evaluate and return JSON only."
        )

        # 4. Call LLM
        logger.info(f"🚀 [Evaluator] conv={conversation_id} submode={submode_id} level={difficulty_level}")
        raw = await service_client.call_ai(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=0.2,
        )

        # 5. Parse result
        result = self._parse_response(raw)
        status = result.get("status", "fail")
        feedback = result.get("feedback", {"observed": [], "interpretation": []})

        # 6. Save attempt
        db.add(TrainingAttempt(
            user_id=user_id,
            conversation_id=conversation_id,
            submode_id=submode_id,
            difficulty_level=difficulty_level,
            status=status,  # "pass" | "fail"
            feedback=json.dumps(feedback),
        ))

        # 7. Mark passed + unlock next (no commit inside progress_service)
        unlocked = []
        if status == "pass":
            await self._set_passed(db, user_id, submode_id, difficulty_level)
            unlocked = await progress_service.unlock_next(db, user_id, submode_id, difficulty_level)

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
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except Exception as e:
            logger.error(f"❌ [Evaluator] Parse failed: {e}\nRaw: {raw[:200]}")
            return {"status": "fail", "feedback": {"observed": [], "interpretation": []}}

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


evaluator = Evaluator()
