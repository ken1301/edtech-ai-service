from fastapi import BackgroundTasks

from typing import List, Dict, Any, Tuple

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.message import Message
from domain.models.overall_models.common import Role
from domain.models.overall_models.response import Lesson2ChatResponse
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata

from application.stateless_services.lesson2_service.orchestration import Lesson2Orchestration
from application.stateless_services.llm_manager import LLMManager
from application.services.session_manager import SessionManager
from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.learning_service import LearningService

from domain.exceptions import (
    LLMManagerError,
    ProfileManagerError,
    SessionManagerError,    
    PromptGenerationError,
    AuthorizationError,
    SyncAndCloseSessionError,
    CompressSessionHistoryError,
    ChatBotUseCaseError,
    Lesson2SessionConflictError,
    Lesson2ValidationError,
    SessionClosedError,
    SessionNotFoundError,
)

from infrastructure.logging import logger


class ChatbotUseCase:
    """Use case for handling chatbot workflow, pipeline orchestrator."""

    TURN_THRESHOLD = 20 # after 20 turns, we start compressing history to save tokens
    TURN_TO_KEEP = 10 # when compressing, keep the last 10 turns of raw messages for better context, compress the rest into a summary
    TURN_TO_COMPRESS = 10 # when compressing, we compress 10 turns of messages into a summary (this is a hyperparameter that can be tuned based on token limits and performance)
    MSG_PER_TURN = 2  # user + assistant

    def __init__(
        self, 
        session_manager: SessionManager,
        learning_service: LearningService,
        orchestration: Lesson2Orchestration,
    ):  
        # Basic service 
        self._session_manager = session_manager

        # Stateless service
        self._learning_service = learning_service 

        # Lesson 2 specific stateless services
        self._orchestration = orchestration


    @staticmethod
    def _if_valid_data(user_id: str, metadata: SessionMetadata):
        # Placeholder for actual validation logic (e.g., check if user exists, session is active, etc.)
        if metadata is None or not metadata.session_id or not metadata.user_id:
            raise SessionNotFoundError("Session not found.")
        if metadata.user_id != user_id:
            raise AuthorizationError("User not authorized for this session.")

    async def run(
        self,
        user_id: str,
        session_id: str,
        correlation_id: str,
        request: Lesson2Request,
        subject: Subject,
        topic: Topic,
        concept: Concept,
        background_task: BackgroundTasks,
    ) -> Lesson2ChatResponse:
        """Main pipeline for processing a user message and generating a chatbot response."""
        request_metadata: SessionMetadata | None = None

        try:
            async with self._session_manager.session_guard(session_id):
                metadata, cached_response = await self._session_manager.prepare_lesson2_chat_request(
                    session_id=session_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
                self._if_valid_data(user_id, metadata)
                request_metadata = metadata

                if cached_response is not None:
                    return cached_response

                if not metadata.is_active:
                    raise SessionClosedError("This session is closed or expired. Please start a new session to continue.")

                history_msg = await self._session_manager.redis_get_all_messages(session_id)

                if metadata.turn_count > self.TURN_THRESHOLD:
                    MSG_TO_COMPRESS = self.TURN_TO_COMPRESS * self.MSG_PER_TURN
                    metadata = await self._learning_service.compress_session_history(
                        session_id=session_id,
                        history_msg=history_msg,
                        metadata=metadata,
                        correlation_id=correlation_id,
                        MSG_TO_COMPRESS=MSG_TO_COMPRESS,
                        TURN_TO_COMPRESS=self.TURN_TO_COMPRESS,
                    )
                    history_msg = history_msg[MSG_TO_COMPRESS:]

                user_msg_obj = Message(
                    role=Role.USER, 
                    content=request.user_msg, 
                    is_submission=request.is_submission,
                    correlation_id=correlation_id,
                )
                history_msg.append(user_msg_obj)

                response_content, updated_metadata, token_usage = await self._orchestration.process(
                    request=request,
                    history_msg=history_msg,
                    session_metadata=metadata,
                )

                assistant_msg_obj = Message(role=Role.ASSISTANT, content=response_content, correlation_id=correlation_id)
                updated_metadata = self._session_manager.complete_lesson2_chat_request(
                    metadata=updated_metadata,
                    correlation_id=correlation_id,
                    response_content=response_content,
                    response_usage=token_usage,
                )

                updated_metadata.turn_count += 1
                await self._session_manager.redis_save_turn_with_metadata(
                    session_id=session_id,
                    user_message=user_msg_obj,
                    assistant_message=assistant_msg_obj,
                    metadata=updated_metadata,
                )

                logger.info(
                    "chatbot.run.succeeded",
                    session_id=session_id,
                    log_type="info",
                    token_usage=token_usage,
                )
                return Lesson2ChatResponse(
                    content=response_content,
                    usage=token_usage,
                    correlation_id=correlation_id,
                    current_progress=updated_metadata.current_progress,
                )
            
        except (
            PromptGenerationError,
            LLMManagerError,
            SessionManagerError,
            ProfileManagerError,
            SyncAndCloseSessionError,
            CompressSessionHistoryError,
        ) as e:
            logger.error(
                "chatbot.run.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise ChatBotUseCaseError("Failed to process chatbot request.") from e

        except (
            AuthorizationError,
            Lesson2ValidationError,
            Lesson2SessionConflictError,
            SessionClosedError,
            SessionNotFoundError,
        ):
            if request_metadata is not None:
                await self._session_manager.abandon_lesson2_chat_request(
                    session_id=session_id,
                    metadata=request_metadata,
                    correlation_id=correlation_id,
                )
            raise
        
        except Exception as e:
            if request_metadata is not None:
                await self._session_manager.abandon_lesson2_chat_request(
                    session_id=session_id,
                    metadata=request_metadata,
                    correlation_id=correlation_id,
                )
            logger.error(
                "chatbot.unexpected.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise ChatBotUseCaseError("An unexpected error occurred.") from e
        

