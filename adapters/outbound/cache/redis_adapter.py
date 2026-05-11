import json
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from domain.ports.session_store_port import SessionStorePort
from domain.models.message import Message, Role
from domain.models.profile import Subject
from domain.exceptions import SessionStoreError

from infrastructure.logging import logger


class RedisSessionAdapter(SessionStorePort):
    """
    Redis adapter for short-term session storage.

    Key schema:
        session:{session_id}:metadata  — String (JSON-encoded dict)
        session:{session_id}:messages  — List   (JSON-encoded Message objects)

    The messages list is treated as a deque:
        - RPUSH             → append new turns to the right (newest)
        - LRANGE(0, N-1)    → get the N oldest  (left)
        - LRANGE(-N, -1)    → get the N newest  (right)
        - LTRIM(N, -1)      → drop the N oldest (left)

    Session timeout:
        `get_metadata` compares the current UTC time against `opened_at` stored
        inside the metadata dict. If the gap exceeds SESSION_TIMEOUT_SECONDS
        (default 1 h), `is_active` is flipped to False and `closed_at` is
        stamped. The mutated metadata is immediately persisted back to Redis
        before being returned, so all subsequent workers see the correct state.

        Callers must store `opened_at` (ISO-8601 UTC string) when first creating
        the session metadata, e.g.:
            metadata = {
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                ...
            }
    """

    _MSG_KEY_TPL  = "session:{session_id}:messages"
    _META_KEY_TPL = "session:{session_id}:metadata"

    _DEFAULT_TTL             = 60 * 60 * 2  # 2 h  — Redis key expiry
    _SESSION_TIMEOUT_SECONDS = 60 * 60      # 1 h  — business-level session limit

    def __init__(
        self,
        redis_client: aioredis.Redis,
        ttl: int = _DEFAULT_TTL,
        session_timeout: int = _SESSION_TIMEOUT_SECONDS,
    ):
        self._redis           = redis_client
        self._ttl             = ttl
        self._session_timeout = session_timeout

    # ── key helpers ───────────────────────────────────────────────────────────

    def _msg_key(self, session_id: str) -> str:
        return self._MSG_KEY_TPL.format(session_id=session_id)

    def _meta_key(self, session_id: str) -> str:
        return self._META_KEY_TPL.format(session_id=session_id)

    # ── (de)serialisation helpers ─────────────────────────────────────────────

    @staticmethod
    def _serialize_message(msg: Message) -> str:
        return json.dumps({
            "role":           msg.role.value,
            "content":        msg.content,
            "correlation_id": msg.correlation_id,
        })

    @staticmethod
    def _deserialize_message(raw: str | bytes) -> Message:
        data = json.loads(raw)
        return Message(
            role=Role(data["role"]),
            content=data["content"],
            correlation_id=data.get("correlation_id"),
        )

    # ── session timeout helper ────────────────────────────────────────────────

    def _check_session_timeout(
        self,
        session_id: str,
        metadata: dict,
    ) -> tuple[dict, bool]:
        """
        Pure logic — no I/O, no exceptions raised.

        Compares now_utc against `opened_at` in metadata.
        If elapsed > SESSION_TIMEOUT_SECONDS and session is still active:
            → flips  is_active  = False
            → stamps closed_at  = now  (once only; stable on retry)
            → returns (metadata, True)  ← caller must persist to Redis

        Returns:
            (metadata, needs_persist)
        """
        if not metadata.get("is_active", True):
            return metadata, False

        opened_at_raw: Optional[str] = metadata.get("opened_at")
        if not opened_at_raw:
            logger.warning(
                "redis_session_adapter.timeout_check.missing_opened_at",
                log_type="technical",
                session_id=session_id,
            )
            return metadata, False

        try:
            opened_at: datetime = datetime.fromisoformat(opened_at_raw)
        except ValueError:
            logger.error(
                "redis_session_adapter.timeout_check.invalid_opened_at",
                log_type="technical",
                session_id=session_id,
                opened_at_raw=opened_at_raw,
            )
            return metadata, False

        if opened_at.tzinfo is None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)

        now             = datetime.now(timezone.utc)
        elapsed_seconds = (now - opened_at).total_seconds()

        if elapsed_seconds > self._session_timeout:
            metadata["is_active"] = False
            if not metadata.get("closed_at"):
                metadata["closed_at"] = now.isoformat()

            logger.info(
                "redis_session_adapter.timeout_check.session_expired",
                log_type="business",
                session_id=session_id,
                opened_at=opened_at_raw,
                closed_at=metadata["closed_at"],
                elapsed_seconds=round(elapsed_seconds),
            )
            return metadata, True

        return metadata, False

    @staticmethod
    def _ensure_metadata_defaults(metadata: dict) -> tuple[dict, bool]:
        """Backfill missing metadata fields for older Redis session records."""
        needs_persist = False

        if "turn_count" not in metadata:
            metadata["turn_count"] = 0
            needs_persist = True

        return metadata, needs_persist

    # ── SessionStorePort interface ────────────────────────────────────────────

    async def get_metadata(self, session_id: str) -> dict:
        """
        Fetch session metadata from Redis.

        Side-effect: if the session has exceeded SESSION_TIMEOUT_SECONDS,
        `is_active` is flipped to False, `closed_at` is stamped, and the
        updated dict is written back to Redis before being returned.
        """
        try:
            raw = await self._redis.get(self._meta_key(session_id))
        except RedisError as e:
            logger.error(
                "redis_session_adapter.get_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch metadata for session '{session_id}' from Redis."
            ) from e

        if not raw:
            logger.warning(
                "redis_session_adapter.get_metadata.not_found",
                log_type="technical",
                session_id=session_id,
            )
            return {}

        try:
            metadata: dict = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(
                "redis_session_adapter.get_metadata.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt metadata JSON for session '{session_id}'."
            ) from e

        metadata, needs_default_persist = self._ensure_metadata_defaults(metadata)
        metadata, needs_timeout_persist = self._check_session_timeout(session_id, metadata)
        needs_persist = needs_default_persist or needs_timeout_persist

        if needs_persist:
            try:
                await self._redis.set(
                    self._meta_key(session_id),
                    json.dumps(metadata),
                    ex=self._ttl,
                )
            except RedisError as e:
                # Non-fatal: caller still receives the correct (expired) metadata.
                logger.error(
                    "redis_session_adapter.get_metadata.timeout_persist_failed",
                    log_type="technical",
                    session_id=session_id,
                    error=str(e),
                )

        return metadata

    async def save_metadata(self, session_id: str, metadata: dict) -> None:
        try:
            await self._redis.set(
                self._meta_key(session_id),
                json.dumps(metadata),
                ex=self._ttl,
            )
        except RedisError as e:
            logger.error(
                "redis_session_adapter.save_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to save metadata for session '{session_id}' to Redis."
            ) from e

    async def save_turn(
        self,
        session_id: str,
        user_message: Message,
        assistant_message: Message,
    ) -> None:
        """Append a (user, assistant) turn to the right of the message list."""
        try:
            msg_key = self._msg_key(session_id)
            pipe    = self._redis.pipeline()
            pipe.rpush(msg_key, self._serialize_message(user_message))
            pipe.rpush(msg_key, self._serialize_message(assistant_message))
            pipe.expire(msg_key, self._ttl)
            await pipe.execute()
        except RedisError as e:
            logger.error(
                "redis_session_adapter.save_turn.failed",
                log_type="technical",
                session_id=session_id,
                user_correlation_id=user_message.correlation_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to save message turn for session '{session_id}' to Redis."
            ) from e

    async def get_right(self, session_id: str, limit: int) -> list[Message]:
        """Return the N most recent messages (right / newest end of list)."""
        try:
            raws = await self._redis.lrange(self._msg_key(session_id), -limit, -1)
        except RedisError as e:
            logger.error(
                "redis_session_adapter.get_right.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch recent messages for session '{session_id}' from Redis."
            ) from e

        try:
            return [self._deserialize_message(r) for r in raws]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "redis_session_adapter.get_right.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt message data in session '{session_id}'."
            ) from e

    async def get_left(self, session_id: str, limit: int) -> list[Message]:
        """Return the N oldest messages (left / oldest end of list)."""
        try:
            raws = await self._redis.lrange(self._msg_key(session_id), 0, limit - 1)
        except RedisError as e:
            logger.error(
                "redis_session_adapter.get_left.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch oldest messages for session '{session_id}' from Redis."
            ) from e

        try:
            return [self._deserialize_message(r) for r in raws]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "redis_session_adapter.get_left.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt message data in session '{session_id}'."
            ) from e

    async def delete_left(self, session_id: str, limit: int) -> None:
        """Drop the N oldest messages via LTRIM (keeps [limit, -1])."""
        try:
            await self._redis.ltrim(self._msg_key(session_id), limit, -1)
        except RedisError as e:
            logger.error(
                "redis_session_adapter.delete_left.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to trim message list for session '{session_id}' in Redis."
            ) from e

    async def delete_session(self, session_id: str) -> None:
        """Delete all Redis keys belonging to this session."""
        try:
            pipe = self._redis.pipeline()
            pipe.delete(self._msg_key(session_id))
            pipe.delete(self._meta_key(session_id))
            await pipe.execute()
        except RedisError as e:
            logger.error(
                "redis_session_adapter.delete_session.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to delete session '{session_id}' from Redis."
            ) from e

    # ── Methods not applicable to Redis ──────────────────────────────────────

    async def save_messages(self, *args, **kwargs):
        raise NotImplementedError("save_messages is a MongoDB operation.")

    async def get_history_messages(self, *args, **kwargs):
        raise NotImplementedError("get_history_messages is a MongoDB operation.")