"""
Per-conversation message queue using asyncio locks.

Guarantees that messages within the same conversation are processed
sequentially — even if the client sends multiple messages in parallel.
Each conversation gets its own lock; concurrent requests queue up and
wait their turn, so the LLM always sees the full, consistent history.
"""

import asyncio
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Global registry: conversation_id → Lock
_locks: dict[str, asyncio.Lock] = {}
_registry_lock = asyncio.Lock()


async def get_conversation_lock(conversation_id: UUID) -> asyncio.Lock:
    """Return (creating if needed) the lock for a given conversation."""
    key = str(conversation_id)
    async with _registry_lock:
        if key not in _locks:
            _locks[key] = asyncio.Lock()
            logger.debug(f"🔒 Created lock for conversation {key}")
        return _locks[key]


async def release_conversation_lock(conversation_id: UUID) -> None:
    """
    Remove the lock from the registry once the conversation is done
    (e.g. deleted). Safe to call even if the lock doesn't exist.
    """
    key = str(conversation_id)
    async with _registry_lock:
        _locks.pop(key, None)
        logger.debug(f"🔓 Released lock registry entry for conversation {key}")
