import time
from typing import List, Tuple

from domain.ports.session_store_port import SessionStorePort
from domain.models.message import Message, Role
from domain.exceptions import SessionExpiredError
from infrastructure.logging import logger


class SessionManager:
    """Manages chat session lifecycle and context compression."""

    SESSION_TIMEOUT_SECONDS = 60 * 60 * 0.1  # 1 hour
    COMPRESSION_THRESHOLD = 10      # compress when turn count exceeds this
    MESSAGES_TO_COMPRESS = 10       # summarise the oldest N messages
    MESSAGES_TO_KEEP = 10           # keep the most recent N messages verbatim

    def __init__(self, session_store: SessionStorePort):
        self.session_store = session_store

    async def get_or_create_session(self, session_id: str) -> Tuple[dict, bool]:
        """Return (metadata, is_active). Creates a new session if none exists."""
        meta = await self.session_store.get_metadata(session_id)

        if not meta:
            meta = {"start_time": time.time(), "is_active": True, "turn_count": 0}
            await self.session_store.save_metadata(session_id, meta)
            logger.info("SESSION_CREATED", session_id=session_id)
            return meta, True

        if time.time() - meta.get("start_time", 0) > self.SESSION_TIMEOUT_SECONDS:
            meta["is_active"] = False
            await self.session_store.save_metadata(session_id, meta)
            logger.warning("SESSION_EXPIRED", session_id=session_id)
            return meta, False

        logger.info("SESSION_RETRIEVED", session_id=session_id)
        return meta, True

    async def increment_turn(self, session_id: str, meta: dict) -> dict:
        """Increment turn counter and persist metadata."""
        meta["turn_count"] = meta.get("turn_count", 0) + 1
        await self.session_store.save_metadata(session_id, meta)
        return meta

    async def save_metadata(self, session_id: str, metadata: dict) -> bool:
        return await self.session_store.save_metadata(session_id, metadata)

    def needs_compression(self, meta: dict) -> bool:
        return meta.get("turn_count", 0) > self.COMPRESSION_THRESHOLD

    async def get_messages_for_compression(self, session_id: str) -> Tuple[List[Message], List[Message]]:
        """Split history into (old_messages_to_compress, recent_messages_to_keep)."""
        history = await self.session_store.get_history(session_id)
        if len(history) <= self.MESSAGES_TO_KEEP:
            return [], history
        split = len(history) - self.MESSAGES_TO_KEEP
        return history[:split], history[split:]

    async def replace_history_with_summary(
        self,
        session_id: str,
        summary_text: str,
        recent_messages: List[Message],
    ) -> None:
        """Clear session history and rebuild with summary + recent messages."""
        await self.session_store.clear_session(session_id)

        # Re-insert summary as a system message placeholder
        summary_msg = Message(role=Role.SYSTEM, content=f"[Tóm tắt những tin nhắn trước]: {summary_text}")
        await self.session_store.save_message(session_id, summary_msg)

        for msg in recent_messages:
            await self.session_store.save_message(session_id, msg)

        logger.info("CONTEXT_COMPRESSED", session_id=session_id, kept=len(recent_messages))
