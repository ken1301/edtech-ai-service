from typing import Dict, Any, List

from application.stateless_services.llm_manager import LLMManager
from application.services.session_manager import SessionManager
from application.stateless_services.prompt_builder import PromptBuilder
from application.services.profile_manager import ProfileManager
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.meta import SessionMetadata, CompressedHistoryMsgInput, SummarizeSessionInput
from domain.models.overall_models.message import ConversationContext, Message
from domain.models.overall_models.profile import SessionSummary, StudentPreference, LearningDetails

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
        profile_manager: ProfileManager,
        adaptive_learning_service: AdaptiveLearningService,
    ):
        self._llm_manager = llm_manager
        self._session_manager = session_manager
        self._prompt_builder = prompt_builder
        self._profile_manager = profile_manager
        self._adaptive_learning_service = adaptive_learning_service

        
    async def sync_and_close_session(
        self,
        user_id: str,
        session_id: str,
        subject: Subject,
        topic: Topic,
        concept: Concept,
        history_msg: List[Message],
        metadata: SessionMetadata,
    ):
        """Background task to sync session data, summarize session, and perform any necessary cleanup when a session expires."""
        
        try:
            # 1. Save the remaining session history to MongoDB for long-term storage and analysis 
            await self._session_manager.mongo_save_messages(
                user_id=user_id,
                session_id=session_id,
                messages=history_msg,
                subject=subject,
                topic=topic,
                concept=concept
            )

            # 2. Generate session summary using LLM  
            summarize_input = self._build_summarization_input(
                history_msg=history_msg,
                session_metadata=metadata,
            )
            summarize_prompt = await self._prompt_builder.lesson2_summarize_prompt(**summarize_input.model_dump())
            summary_response = await self._llm_manager.generate_response(
                system_prompt=summarize_prompt,
                messages=[],
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
                concept=concept,
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
        history_msg: List[Message],
        metadata: SessionMetadata,
        MSG_TO_COMPRESS: int,
        TURN_TO_COMPRESS: int,
    ) -> SessionMetadata:
        """Compress the session history in Redis by summarizing older messages using the LLM."""
        try:
            compress_input = await self._build_compression_input(
                history_msg=history_msg[:MSG_TO_COMPRESS],
                session_metadata=metadata,
            )
            compress_prompt = await self._prompt_builder.lesson2_compress_prompt(**compress_input.model_dump())
            compress_output = await self._llm_manager.generate_response(
                system_prompt=compress_prompt,
                messages=[],
                context=self.conversation_context,
            )

            metadata.history_compression = compress_output.content
            metadata.turn_count -= TURN_TO_COMPRESS

            await self._session_manager.mongo_save_messages(
                user_id=metadata.user_id,
                session_id=session_id,
                messages=history_msg[:MSG_TO_COMPRESS], # save the raw messages except the last TURN_TO_KEEP turns which are kept for better context
                subject=metadata.subject,
                topic=metadata.topic,
                concept=metadata.concept
            )

            await self._session_manager.redis_delete_left(session_id, limit=MSG_TO_COMPRESS)

            logger.info(
                "compress_history.completed",
                log_type="business",
                session_id=session_id,
                token_usage=compress_output.usage,
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

    @staticmethod
    def _build_compression_input(
        history_msg: List[Message],
        session_metadata: SessionMetadata,
    ) -> CompressedHistoryMsgInput:
        """Helper method to build the input for the compression prompt."""
        return CompressedHistoryMsgInput()

    @staticmethod
    def _build_summarization_input(
        history_msg: List[Message],
        session_metadata: SessionMetadata,
    ) -> SummarizeSessionInput:
        """Helper method to build the input for the session summarization prompt."""
        return SummarizeSessionInput()