import asyncio
from contextlib import asynccontextmanager

from domain.ports.session_store_port import SessionStorePort

from domain.models.overall_models.message import Message
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.meta import SessionMetadata
from domain.models.overall_models.response import Lesson2ChatResponse

from infrastructure.logging import logger   

from domain.exceptions import Lesson2SessionConflictError, SessionManagerError, SessionStoreError

class SessionManager:
    """Service responsible for managing session state, including syncing session data to the database and closing sessions."""

    def __init__(
        self,
        redis_session_store: SessionStorePort,
        mongo_session_store: SessionStorePort
    ):
        self._redis_store = redis_session_store
        self._mongo_store = mongo_session_store
        self._session_locks: dict[str, asyncio.Lock] = {}

    @asynccontextmanager
    async def session_guard(self, session_id: str):
        lock = self._session_locks.setdefault(session_id, asyncio.Lock())
        async with lock:
            yield

    async def prepare_lesson2_chat_request(
        self,
        session_id: str,
        user_id: str,
        correlation_id: str,
    ) -> tuple[SessionMetadata, Lesson2ChatResponse | None]:
        """Reserve a session for one chat request or replay the last completed response."""
        metadata = await self.redis_get_metadata(session_id)

        if metadata is None or not metadata.session_id or metadata.user_id != user_id:
            return metadata, None

        if (
            metadata.last_completed_correlation_id == correlation_id
            and metadata.last_response_content is not None
            and metadata.last_response_progress is not None
        ):
            return metadata, Lesson2ChatResponse(
                content=metadata.last_response_content,
                usage=list(metadata.last_response_usage),
                correlation_id=correlation_id,
                current_progress=metadata.last_response_progress,
            )

        if metadata.active_correlation_id == correlation_id:
            raise Lesson2SessionConflictError("A request with this correlation_id is already in progress.")

        if metadata.active_correlation_id is not None:
            raise Lesson2SessionConflictError("Another request is already in progress for this session.")

        metadata.active_correlation_id = correlation_id
        await self.redis_save_metadata(session_id, metadata)
        return metadata, None

    async def abandon_lesson2_chat_request(
        self,
        session_id: str,
        metadata: SessionMetadata,
        correlation_id: str,
    ):
        """Clear an in-flight correlation marker after a failed chat request."""
        if metadata.active_correlation_id != correlation_id:
            return

        metadata.active_correlation_id = None
        await self.redis_save_metadata(session_id, metadata)

    @staticmethod
    def complete_lesson2_chat_request(
        metadata: SessionMetadata,
        correlation_id: str,
        response_content: str,
        response_usage: list,
    ) -> SessionMetadata:
        metadata.active_correlation_id = None
        metadata.last_completed_correlation_id = correlation_id
        metadata.last_response_content = response_content
        metadata.last_response_usage = list(response_usage)
        metadata.last_response_progress = metadata.current_progress
        return metadata

    # ================= Redis operations =================

    async def redis_get_metadata(self, session_id: str) -> SessionMetadata:
        """Get session metadata from Redis."""
        try: 
            metadata = await self._redis_store.get_metadata(session_id)
            
            logger.info(
                "session_manager.redis_get_metadata.completed",
                log_type="business",
                session_id=session_id,
            )

            return metadata
        

        except SessionStoreError as e: 
            raise SessionManagerError("Failed to get session metadata from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_metadata.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while getting session metadata from Redis.") from e
        

    async def redis_save_metadata(self, session_id: str, metadata: SessionMetadata):
        """Save session metadata to Redis."""
        try: 
            await self._redis_store.save_metadata(session_id, metadata)

            logger.info(
                "session_manager.redis_save_metadata.completed",
                log_type="business",
                session_id=session_id,
            )        
            
        except SessionStoreError as e:
            raise SessionManagerError("Failed to save session metadata to Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_save_metadata.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while saving session metadata to Redis.") from e

    async def redis_mark_session_closing(self, session_id: str, user_id: str) -> tuple[SessionMetadata, bool]:
        """Mark a session as closing exactly once and return (metadata, newly_marked)."""
        try:
            async with self.session_guard(session_id):
                metadata = await self._redis_store.get_metadata(session_id)
                if not metadata or not metadata.session_id or metadata.user_id != user_id:
                    return metadata, False

                if metadata.closed_at is not None:
                    return metadata, False

                if metadata.is_closing:
                    return metadata, False

                metadata.is_closing = True
                metadata.is_active = False
                await self._redis_store.save_metadata(session_id, metadata)

            logger.info(
                "session_manager.redis_mark_session_closing.completed",
                log_type="business",
                session_id=session_id,
            )
            return metadata, True

        except SessionStoreError as e:
            raise SessionManagerError("Failed to mark session as closing in Redis.") from e

        except Exception as e:
            logger.error(
                "session_manager.redis_mark_session_closing.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while marking session as closing in Redis.") from e

    async def redis_get_all_messages(self, session_id: str) -> list[Message]:
        """Get the full message history for a session from Redis."""
        try: 
            messages = await self._redis_store.get_history_messages(session_id)
            
            logger.info(
                "session_manager.redis_get_all_messages.completed",
                log_type="business",
                session_id=session_id,
            )
            
            return messages
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to get all messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_all_messages.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while getting all messages from Redis.") from e
    
    async def redis_get_right(self, session_id: str, limit: int) -> list[Message]:
        """Get the most recent messages from Redis for the session."""
        try: 
            messages = await self._redis_store.get_right(session_id, limit)
            
            logger.info(
                "session_manager.redis_get_right.completed",
                log_type="business",
                session_id=session_id,
            )
            
            return messages
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to get messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_right.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while getting messages from Redis.") from e
        

    async def redis_save_turn(
        self, 
        session_id: str, 
        user_message: Message, 
        assistant_message: Message
    ):
        """Save a turn (user message + assistant message) to Redis."""
        try: 
            await self._redis_store.save_turn(session_id, user_message, assistant_message)

            logger.info(
                "session_manager.redis_save_turn.completed",
                log_type="business",
                session_id=session_id,
            )
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to save message turn to Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_save_turn.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while saving message turn to Redis.") from e

    async def redis_save_turn_with_metadata(
        self,
        session_id: str,
        user_message: Message,
        assistant_message: Message,
        metadata: SessionMetadata,
    ):
        """Persist a completed turn and updated metadata together so turn_count stays aligned."""
        try:
            await self._redis_store.save_turn_with_metadata(
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                metadata=metadata,
            )

            logger.info(
                "session_manager.redis_save_turn_with_metadata.completed",
                log_type="business",
                session_id=session_id,
            )

        except SessionStoreError as e:
            raise SessionManagerError("Failed to save message turn and metadata to Redis.") from e

        except Exception as e:
            logger.error(
                "session_manager.redis_save_turn_with_metadata.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while saving message turn and metadata to Redis.") from e
    
    
    async def redis_get_left(self, session_id: str, limit: int) -> list[Message]:
        """Get the oldest messages from Redis for the session (used for history compression)."""
        try: 
            messages = await self._redis_store.get_left(session_id, limit)
            
            logger.info(
                "session_manager.redis_get_left.completed",
                log_type="business",   
                session_id=session_id,
            )
            
            return messages
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to get messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_left.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while getting messages from Redis.") from e
        
    async def redis_delete_left(self, session_id: str, limit: int):
        """Delete the oldest messages from Redis for the session (used for history compression)."""
        try: 
            await self._redis_store.delete_left(session_id, limit)

            logger.info(
                "session_manager.redis_delete_left.completed",
                log_type="business",
                session_id=session_id,
            )
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to delete messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_delete_left.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while deleting messages from Redis.") from e
        
    async def redis_delete_session(self, session_id: str):
        """Delete all session data from Redis (used when closing a session)."""
        try: 
            await self._redis_store.delete_session(session_id)
        
            logger.info(
                "session_manager.redis_delete_session.completed",
                log_type="business",
                session_id=session_id,
            )
        
        except SessionStoreError as e:
            raise SessionManagerError("Failed to delete session from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_delete_session.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while deleting session from Redis.") from e
        
    # ================= MongoDB operations =================
    async def mongo_save_messages(
        self,
        user_id: str,
        session_id: str,
        messages: list[Message],
        subject: Subject,
        topic: Topic,
        concept: Concept,
        archive_kind: str,
        archive_request_id: str,
    ):
        """Save the messages when compressing session history"""

        try:
            await self._mongo_store.save_messages(
                user_id=user_id,
                session_id=session_id,
                messages=messages,
                subject=subject,
                topic=topic,
                concept=concept,
                archive_kind=archive_kind,
                archive_request_id=archive_request_id,
            )

            logger.info(
                "session_manager.mongo_save_messages.completed",
                log_type="business",
                session_id=session_id,
            )

        except SessionStoreError as e:
            raise SessionManagerError("Failed to save messages to MongoDB.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.mongo_save_messages.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                subject=subject,
                topic=topic,
                concept=concept,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while saving messages to MongoDB.") from e
        
    async def mongo_get_history_messages(self, session_id: str, user_id: str) -> list[Message]:
        """Get all session messages from MongoDB (used for session summarization when closing session)"""

        try:
            messages = await self._mongo_store.get_history_messages(session_id, user_id)

            logger.info(
                "session_manager.mongo_get_history_messages.completed",
                log_type="business",
                session_id=session_id,
                user_id=user_id,
            )

            return messages

        except SessionStoreError as e:
            raise SessionManagerError("Failed to get session messages from MongoDB.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.mongo_get_history_messages.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise SessionManagerError("Unexpected error while getting session messages from MongoDB.") from e
        