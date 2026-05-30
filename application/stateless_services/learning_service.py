from typing import Dict, Any

from application.stateless_services.llm_manager import LLMManager
from application.services.session_manager import SessionManager
from application.stateless_services.prompt_builder import PromptBuilder
from application.services.profile_manager import ProfileManager

from domain.models.curriculum import Subject
from domain.models.message import ConversationContext
from domain.models.session import SessionSummary

from infrastructure.logging import logger

from domain.exceptions import (
    LLMManagerError,
    SessionManagerError,
    ProfileManagerError,
    PromptGenerationError,
    SyncAndCloseSessionError,
    CompressSessionHistoryError,
)

class LearningService:
    """Stateless service for learning-related functionalities, such as context compression and session summarization."""

    conversation_context = ConversationContext(
            temperature=0.3,
            # response_format="json",
        )

    def __init__(
        self,
        llm_manager: LLMManager,
        session_manager: SessionManager,
        prompt_builder: PromptBuilder,
        profile_manager: ProfileManager
    ):
        self._llm_manager = llm_manager
        self._session_manager = session_manager
        self._prompt_builder = prompt_builder
        self._profile_manager = profile_manager
        

    async def sync_and_close_session(
        self,
        user_id: str,
        session_id: str,
        subject: Subject,
        topic: str,
        metadata: Dict[str, Any],
    ):
        """Background task to sync session data, summarize session, and perform any necessary cleanup when a session expires."""
        
        try:
            # 1. Save the remaining session history to MongoDB for long-term storage and analysis 
            history = await self._session_manager.redis_get_right(session_id)
            await self._session_manager.mongo_save_messages(
                user_id=user_id,
                session_id=session_id,
                messages=history,
                subject=subject,
                topic=topic,
            )

            # 2. Generate session summary using LLM  
            system_prompt = await self._prompt_builder.summarize_session_prompt()
            all_messages = await self._session_manager.mongo_get_history_messages(session_id)
            summary_response = await self._llm_manager.generate_response(
                system_prompt=system_prompt,
                messages=all_messages,
                context=self.conversation_context,
                response_model=SessionSummary
            )
            
            # 3. Save the student preference and knowledge map to MongoDB
            student_preference = summary_response.content.student_preference
            topic_mastery = summary_response.content.topic_mastery
            await self._profile_manager.update_student_profile(
                user_id=user_id,
                subject=subject,
                topic=topic,
                student_preference=student_preference,
                topic_mastery=topic_mastery
            )

            # 4. Disable session and delete the session data from Redis to free up memory
            metadata["is_active"] = False
            await self._session_manager.redis_save_metadata(session_id, metadata)
            await self._session_manager.redis_delete_session(session_id)

            logger.info(
                "sync_and_close_session.completed",
                log_type="business",
                session_id=session_id,
            )

        except (LLMManagerError, SessionManagerError, ProfileManagerError, PromptGenerationError) as e:
            raise SyncAndCloseSessionError("Failed to sync and close the session.") from e

        except Exception as e:
            logger.error(
                "sync_and_close_session.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise SyncAndCloseSessionError("Unexpected error during sync and close.") from e
        
    async def compress_session_history(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        MSG_TO_COMPRESS: int,
        TURN_TO_COMPRESS: int,
    ) -> Dict[str, Any]:
        """Compress the session history in Redis by summarizing older messages using the LLM."""
        try:
            # 1. Get the MSG_TO_COMPRESS oldest messages from Redis
            msg_to_compress = await self._session_manager.redis_get_left(session_id, limit=MSG_TO_COMPRESS)

            # 2. Generate compression prompt and call LLM to get compressed summary of those messages
            compress_prompt = await self._prompt_builder.compress_history_prompt()
            compress_context = await self._llm_manager.generate_response(
                system_prompt=compress_prompt,
                messages=msg_to_compress,
                context=self.conversation_context
            )

            # 3. Delete the MSG_TO_COMPRESS oldest messages from Redis
            await self._session_manager.redis_delete_left(session_id, limit=MSG_TO_COMPRESS)

            # 4. Update the session metadata and save it to Redis
            metadata["summary"] = metadata["summary"] + "\n" + compress_context.content
            metadata["turn_count"] -= TURN_TO_COMPRESS
            await self._session_manager.redis_save_metadata(session_id, metadata)

            logger.info(
                "compress_history.completed",
                log_type="business",
                session_id=session_id,
            )

            return metadata


        except (LLMManagerError, SessionManagerError, PromptGenerationError) as e:
            raise CompressSessionHistoryError("Failed to compress session history.") from e


        except Exception as e:
            logger.error(
                "compress_history.unexpected.failed",
                log_type="technical",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise CompressSessionHistoryError("Unexpected error during history compression.") from e
        