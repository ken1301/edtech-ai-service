import json
from datetime import datetime, timezone

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from domain.ports.session_store_port import SessionStorePort

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import Role
from domain.models.lesson2_models.meta import SessionMetadata

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
        `get_metadata` compares the current UTC time against `created_at` stored
        inside the metadata dict. If the gap exceeds SESSION_TIMEOUT_SECONDS
        (default 1 h), `is_active` is flipped to False and `closed_at` is
        stamped. The mutated metadata is immediately persisted back to Redis
        before being returned, so all subsequent workers see the correct state.

        Callers must store `created_at` (ISO-8601 UTC string) when first creating
        the session metadata, e.g.:
            metadata = {
                "created_at": datetime.now(timezone.utc).isoformat(),
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
        metadata: SessionMetadata,
    ) -> tuple[SessionMetadata, bool]:
        """
        Pure logic — no I/O, no exceptions raised.

        Compares now_utc against `created_at` in metadata.
        If elapsed > SESSION_TIMEOUT_SECONDS and session is still active:
            → flips  is_active  = False
            → stamps closed_at  = now  (once only; stable on retry)
            → returns (metadata, True)  ← caller must persist to Redis

        Returns:
            (metadata, needs_persist)
        """
        if not metadata.is_active:
            return metadata, False

        if not metadata.created_at:
            return metadata, False

        try:
            created_at = metadata.created_at
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
        except ValueError:
            logger.error(
                "redis_adapter.timeout_check.invalid_created_at",
                log_type="technical",
                session_id=session_id,
                created_at_raw=str(metadata.created_at),
            )
            return metadata, False

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        now             = datetime.now(timezone.utc)
        elapsed_seconds = (now - created_at).total_seconds()

        if elapsed_seconds > self._session_timeout:
            metadata.is_active = False
            if not metadata.closed_at:
                metadata.closed_at = now
            return metadata, True

        return metadata, False

    @staticmethod
    def _ensure_metadata_defaults(metadata: SessionMetadata) -> tuple[SessionMetadata, bool]:
        """Backfill missing metadata fields for older Redis session records."""
        needs_persist = False

        if metadata.turn_count == 0 and not hasattr(metadata, '_turn_count_set'):
            metadata.turn_count = 0
            needs_persist = True

        return metadata, needs_persist

    # ── SessionStorePort interface ────────────────────────────────────────────

    async def get_metadata(self, session_id: str) -> SessionMetadata:
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
                "redis_adapter.get_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch metadata for session '{session_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_metadata.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while fetching session metadata.") from e

        if not raw:
            return SessionMetadata()

        try:
            data = json.loads(raw)
            metadata = SessionMetadata(**data)
        except json.JSONDecodeError as e:
            logger.error(
                "redis_adapter.get_metadata.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt metadata JSON for session '{session_id}'."
            ) from e

        try:
            metadata, needs_default_persist = self._ensure_metadata_defaults(metadata)
            metadata, needs_timeout_persist = self._check_session_timeout(session_id, metadata)
            needs_persist = needs_default_persist or needs_timeout_persist

            if needs_persist:
                await self._redis.set(
                    self._meta_key(session_id),
                    metadata.model_dump_json(),
                    ex=self._ttl,
                )
        except RedisError as e:
            logger.error(
                "redis_adapter.get_metadata.persist_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(f"Failed to persist metadata for session '{session_id}' in Redis.") from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_metadata.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while processing session metadata.") from e

        logger.debug(
            "redis_adapter.get_metadata.completed",
            log_type="debug",
            session_id=session_id,
        )
        return metadata

    async def save_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        try:
            await self._redis.set(
                self._meta_key(session_id),
                metadata.model_dump_json(),
                ex=self._ttl,
            )
            logger.debug(
                "redis_adapter.save_metadata.completed",
                log_type="debug",
                session_id=session_id,
            )
        except RedisError as e:
            logger.error(
                "redis_adapter.save_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to save metadata for session '{session_id}' to Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.save_metadata.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while saving session metadata.") from e

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
            logger.debug(
                "redis_adapter.save_turn.completed",
                log_type="debug",
                session_id=session_id,
            )
        except RedisError as e:
            logger.error(
                "redis_adapter.save_turn.failed",
                log_type="technical",
                session_id=session_id,
                user_correlation_id=user_message.correlation_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to save message turn for session '{session_id}' to Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.save_turn.unexpected_error",
                log_type="technical",
                session_id=session_id,
                user_correlation_id=user_message.correlation_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while saving a message turn.") from e

    async def get_history_messages(self, session_id: str) -> list[Message]:
        """Return the full message history for a session, ordered by insertion time."""
        try:
            raws = await self._redis.lrange(self._msg_key(session_id), 0, -1)
            logger.debug(
                "redis_adapter.get_all_messages.completed",
                log_type="debug",
                session_id=session_id,
                count=len(raws),
            )
            return [self._deserialize_message(r) for r in raws]
        except RedisError as e:
            logger.error(
                "redis_adapter.get_all_messages.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch all messages for session '{session_id}' from Redis."
            ) from e
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "redis_adapter.get_all_messages.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt message data in session '{session_id}'."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_all_messages.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while fetching all session messages.") from e

    async def get_right(self, session_id: str, limit: int) -> list[Message]:
        """Return the N most recent messages (right / newest end of list)."""
        try:
            raws = await self._redis.lrange(self._msg_key(session_id), -limit, -1)
        except RedisError as e:
            logger.error(
                "redis_adapter.get_right.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch recent messages for session '{session_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_right.unexpected_error",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while fetching recent session messages.") from e

        try:
            logger.debug(
                "redis_adapter.get_right.completed",
                log_type="debug",
                session_id=session_id,
                limit=limit,
            )
            return [self._deserialize_message(r) for r in raws]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "redis_adapter.get_right.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt message data in session '{session_id}'."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_right.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while deserializing recent session messages.") from e

    async def get_left(self, session_id: str, limit: int) -> list[Message]:
        """Return the N oldest messages (left / oldest end of list)."""
        try:
            raws = await self._redis.lrange(self._msg_key(session_id), 0, limit - 1)
        except RedisError as e:
            logger.error(
                "redis_adapter.get_left.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to fetch oldest messages for session '{session_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_left.unexpected_error",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while fetching oldest session messages.") from e

        try:
            logger.debug(
                "redis_adapter.get_left.completed",
                log_type="debug",
                session_id=session_id,
                limit=limit,
            )
            return [self._deserialize_message(r) for r in raws]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(
                "redis_adapter.get_left.deserialize_failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Corrupt message data in session '{session_id}'."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.get_left.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while deserializing oldest session messages.") from e

    async def delete_left(self, session_id: str, limit: int) -> None:
        """Drop the N oldest messages via LTRIM (keeps [limit, -1])."""
        try:
            logger.debug(
                "redis_adapter.delete_left.completed",
                log_type="debug",
                session_id=session_id,
                limit=limit,
            )
            await self._redis.ltrim(self._msg_key(session_id), limit, -1)
        except RedisError as e:
            logger.error(
                "redis_adapter.delete_left.failed",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to trim message list for session '{session_id}' in Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.delete_left.unexpected_error",
                log_type="technical",
                session_id=session_id,
                limit=limit,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while trimming session messages.") from e

    async def delete_session(self, session_id: str) -> None:
        """Delete all Redis keys belonging to this session."""
        try:
            pipe = self._redis.pipeline()
            pipe.delete(self._msg_key(session_id))
            pipe.delete(self._meta_key(session_id))
            await pipe.execute()
            logger.debug(
                "redis_adapter.delete_session.completed",
                log_type="debug",
                session_id=session_id,
            )
        except RedisError as e:
            logger.error(
                "redis_adapter.delete_session.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to delete session '{session_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_adapter.delete_session.unexpected_error",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while deleting a session.") from e

    # ── Methods not applicable to Redis ──────────────────────────────────────

    async def save_messages(self, *args, **kwargs):
        raise NotImplementedError("save_messages is a MongoDB operation.")
