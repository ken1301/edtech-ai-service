from datetime import datetime, timezone
import asyncio

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from domain.ports.session_store_port import SessionStorePort
from domain.models.overall_models.message import Message
from domain.models.overall_models.common import Role
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.exceptions import SessionStoreError

from infrastructure.logging import logger


class MongoSessionAdapter(SessionStorePort):
    """
    MongoDB adapter for long-term session message storage.

    Collection: `session_messages`

    Document shape:
    {
        "_id": ObjectId,
        "session_id": str,
        "user_id": str,
        "subject": str,
        "topic": str,
        "messages": [
            {"role": str, "content": str, "correlation_id": str | None}
        ],
        "created_at": datetime
    }

    A session may accumulate multiple documents over its lifetime
    (one per compress_session_history call + one final sync_and_close call).
    get_history_messages() merges them all in insertion order.
    """

    _COLLECTION = "session_messages"
    _ARCHIVE_IDEMPOTENCY_INDEX_NAME = "user_id_session_id_archive_kind_archive_request_id_unique"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[self._COLLECTION]
        self._index_lock = asyncio.Lock()
        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return

        async with self._index_lock:
            if self._indexes_ready:
                return

            await self._col.create_index(
                [
                    ("user_id", ASCENDING),
                    ("session_id", ASCENDING),
                    ("archive_kind", ASCENDING),
                    ("archive_request_id", ASCENDING),
                ],
                unique=True,
                name=self._ARCHIVE_IDEMPOTENCY_INDEX_NAME,
            )
            self._indexes_ready = True

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize_message(msg: Message) -> dict:
        return {
            "role":           msg.role.value,
            "content":        msg.content,
            "correlation_id": msg.correlation_id,
        }

    @staticmethod
    def _deserialize_message(data: dict) -> Message:
        return Message(
            role=Role(data["role"]),
            content=data["content"],
            correlation_id=data.get("correlation_id"),
        )

    # ── SessionStorePort interface ────────────────────────────────────────────

    async def save_messages(
        self,
        user_id: str,
        session_id: str,
        messages: list[Message],
        subject: Subject,
        topic: Topic,
        concept: Concept,
        archive_kind: str,
        archive_request_id: str,
    ) -> None:
        """Persist a batch of messages to MongoDB (called during compression or session close)."""
        if not messages:
            logger.warning(
                "mongo_session_store.save_messages.completed.no_messages",
                log_type="debug",
                session_id=session_id,
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                archive_kind=archive_kind,
                archive_request_id=archive_request_id,
            )
            return

        now = datetime.now(timezone.utc)

        try:
            await self._ensure_indexes()
            result = await self._col.update_one(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "archive_kind": archive_kind,
                    "archive_request_id": archive_request_id,
                },
                {
                    "$setOnInsert": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "subject": subject.value,
                        "topic": topic.value,
                        "concept": concept.value,
                        "archive_kind": archive_kind,
                        "archive_request_id": archive_request_id,
                        "messages": [self._serialize_message(m) for m in messages],
                        "created_at": now,
                    }
                },
                upsert=True,
            )
            logger.debug(
                "mongo_session_store.save_messages.completed",
                log_type="debug",
                session_id=session_id,
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                archive_kind=archive_kind,
                archive_request_id=archive_request_id,
                message_count=len(messages),
                inserted=bool(getattr(result, "upserted_id", None)),
            )
        except PyMongoError as e:
            logger.error(
                "mongo_session_store.save_messages.failed",
                log_type="technical",
                session_id=session_id,
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                archive_kind=archive_kind,
                archive_request_id=archive_request_id,
                message_count=len(messages),
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to save messages for session '{session_id}' to MongoDB."
            ) from e
        except Exception as e:
            logger.error(
                "mongo_session_store.save_messages.unexpected_error",
                log_type="technical",
                session_id=session_id,
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                archive_kind=archive_kind,
                archive_request_id=archive_request_id,
                message_count=len(messages),
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while saving session messages.") from e

    async def get_history_messages(self, session_id: str, user_id: str) -> list[Message]:
        """
        Retrieve all messages for a session from MongoDB, sorted by insertion time.
        Merges multiple documents (from separate compress batches) in order.
        """
        try:
            cursor = self._col.find(
                {"session_id": session_id, "user_id": user_id},
                sort=[("created_at", 1)],
            )

            all_messages: list[Message] = []
            async for doc in cursor:
                for raw_msg in doc.get("messages", []):
                    all_messages.append(self._deserialize_message(raw_msg))

        except PyMongoError as e:
            logger.error(
                "mongo_session_store.get_history_messages.failed",
                log_type="technical",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise SessionStoreError(
                f"Failed to retrieve history messages for session '{session_id}' from MongoDB."
            ) from e
        except Exception as e:
            logger.error(
                "mongo_session_store.get_history_messages.unexpected_error",
                log_type="technical",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise SessionStoreError("An unexpected error occurred while retrieving session history.") from e

        logger.debug(
            "mongo_session_store.get_history_messages.completed",
            log_type="debug",
            session_id=session_id,
            user_id=user_id,
            message_count=len(all_messages),
        )
        return all_messages

    # ── Methods not applicable to MongoDB ────────────────────────────────────

    async def get_metadata(self, *args, **kwargs):
        raise NotImplementedError("get_metadata is a Redis operation.")

    async def save_metadata(self, *args, **kwargs):
        raise NotImplementedError("save_metadata is a Redis operation.")

    async def save_turn(self, *args, **kwargs):
        raise NotImplementedError("save_turn is a Redis operation.")

    async def save_turn_with_metadata(self, *args, **kwargs):
        raise NotImplementedError("save_turn_with_metadata is a Redis operation.")

    async def get_right(self, *args, **kwargs):
        raise NotImplementedError("get_right is a Redis operation.")

    async def get_left(self, *args, **kwargs):
        raise NotImplementedError("get_left is a Redis operation.")

    async def delete_left(self, *args, **kwargs):
        raise NotImplementedError("delete_left is a Redis operation.")

    async def delete_session(self, *args, **kwargs):
        raise NotImplementedError("delete_session is a Redis operation.")