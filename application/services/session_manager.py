from domain.ports.session_store_port import SessionStorePort

from domain.models.message import Message
from domain.models.profile import Subject

from infrastructure.logging import logger   

from domain.exceptions import SessionManagerError, SessionStoreError

class SessionManager:
    """Service responsible for managing session state, including syncing session data to the database and closing sessions."""

    def __init__(
        self,
        redis_session_store: SessionStorePort,
        mongo_session_store: SessionStorePort
    ):
        self._redis_store = redis_session_store
        self._mongo_store = mongo_session_store

    # ================= Redis operations =================

    async def redis_get_metadata(self, session_id: str) -> dict:
        """Get session metadata from Redis."""
        try: 
            metadata = await self._redis_store.get_metadata(session_id)
            return metadata
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_get_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to get session metadata from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_metadata.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while getting session metadata from Redis.") from e
        

    async def redis_save_metadata(self, session_id: str, metadata: dict):
        """Save session metadata to Redis."""
        try: 
            await self._redis_store.save_metadata(session_id, metadata)
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_save_metadata.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to save session metadata to Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_save_metadata.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while saving session metadata to Redis.") from e

    async def redis_get_right(self, session_id: str, limit: int) -> list[Message]:
        """Get the most recent messages from Redis for the session."""
        try: 
            messages = await self._redis_store.get_right(session_id, limit)
            return messages
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_get_right.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to get messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_right.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
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
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_save_turn.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to save message turn to Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_save_turn.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while saving message turn to Redis.") from e
    
    
    async def redis_get_left(self, session_id: str, limit: int) -> list[Message]:
        """Get the oldest messages from Redis for the session (used for history compression)."""
        try: 
            messages = await self._redis_store.get_left(session_id, limit)
            return messages
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_get_left.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to get messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_get_left.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),            )
            raise SessionManagerError("Unexpected error while getting messages from Redis.") from e
        
    async def redis_delete_left(self, session_id: str, limit: int):
        """Delete the oldest messages from Redis for the session (used for history compression)."""
        try: 
            await self._redis_store.delete_left(session_id, limit)
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_delete_left.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to delete messages from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_delete_left.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while deleting messages from Redis.") from e
        
    async def redis_delete_session(self, session_id: str):
        """Delete all session data from Redis (used when closing a session)."""
        try: 
            await self._redis_store.delete_session(session_id)
        
        except SessionStoreError as e:
            logger.error(
                "session_manager.redis_delete_session.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to delete session from Redis.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.redis_delete_session.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while deleting session from Redis.") from e
        
    # ================= MongoDB operations =================
    async def mongo_save_messages(
        self,
        student_id: str,
        session_id: str,
        messages: list[Message],
        subject: Subject,
        topic: str,
    ):
        """Save the messages when compressing session history"""

        try:
            await self._mongo_store.save_messages(
                student_id=student_id,
                session_id=session_id,
                messages=messages,
                subject=subject,
                topic=topic,
            )

        except SessionStoreError as e:
            logger.error(
                "session_manager.mongo_save_messages.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to save messages to MongoDB.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.mongo_save_messages.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while saving messages to MongoDB.") from e
        
    async def mongo_get_history_messages(self, session_id: str) -> list[Message]:
        """Get all session messages from MongoDB (used for session summarization when closing session)"""

        try:
            messages = await self._mongo_store.get_history_messages(session_id)
            return messages

        except SessionStoreError as e:
            logger.error(
                "session_manager.mongo_get_history_messages.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Failed to get session messages from MongoDB.") from e
        
        except Exception as e:
            logger.error(
                "session_manager.mongo_get_history_messages.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
            )
            raise SessionManagerError("Unexpected error while getting session messages from MongoDB.") from e
        