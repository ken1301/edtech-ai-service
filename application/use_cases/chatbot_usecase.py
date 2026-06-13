from fastapi import BackgroundTasks

from typing import List, Dict, Any, Tuple

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.message import Message
from domain.models.overall_models.common import Role
from domain.models.overall_models.response import ChatResponse
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
        if not metadata: 
            raise AuthorizationError("Session not found.")
        if metadata.user_id != user_id:
            raise AuthorizationError("User not authorized for this session.")
        return metadata

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
    ):
        """Main pipeline for processing a user message and generating a chatbot response."""
        
        try:
            history_msg = await self._session_manager.redis_get_all_messages(session_id)
            metadata = await self._session_manager.redis_get_metadata(session_id)
            self._if_valid_data(user_id, metadata)

            is_active = metadata.is_active
            if not is_active:
                background_task.add_task(
                    self._learning_service.sync_and_close_session,
                    user_id=user_id,
                    session_id=session_id,
                    subject=subject,
                    topic=topic,
                    concept=concept,
                )
                # return because if we raise an exception here, FastAPI would not execute the background task
                return ChatResponse(
                    content="This session has expired. System is syncing data and closing the session. Please start a new session to continue.",
                    usage=None,
                    correlation_id=correlation_id,
                )

            if metadata.turn_count > self.TURN_THRESHOLD: 
                MSG_TO_COMPRESS = self.TURN_TO_COMPRESS * self.MSG_PER_TURN
                metadata = await self._learning_service.compress_session_history(
                    session_id=session_id,
                    history_msg=history_msg,
                    metadata=metadata,
                    MSG_TO_COMPRESS=MSG_TO_COMPRESS,
                    TURN_TO_COMPRESS=self.TURN_TO_COMPRESS,
                )
                
                await self._session_manager.redis_delete_left(session_id, limit=MSG_TO_COMPRESS)

            response_content, updated_metadata, token_usage = await self._orchestration.process(
                request=request,
                history_msg=history_msg,
                session_metadata=metadata,
            )

            await self._session_manager.redis_save_metadata(session_id, updated_metadata)

            user_msg_obj = Message(role=Role.USER, content=request.message)
            assistant_msg_obj = Message(role=Role.ASSISTANT, content=response_content)
            await self._session_manager.redis_save_turn(
                session_id=session_id,
                user_message=user_msg_obj,
                assistant_message=assistant_msg_obj,
            )

            logger.info(
                "chatbot.run.succeeded",
                session_id=session_id,
                log_type="info",
                token_usage=token_usage,
            )
            return ChatResponse(
                content=response_content,
                usage=token_usage,
                correlation_id=correlation_id,
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
        
        except Exception as e:
            logger.error(
                "chatbot.unexpected.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise ChatBotUseCaseError("An unexpected error occurred.") from e
        

