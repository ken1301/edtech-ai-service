from fastapi import BackgroundTasks, HTTPException, status

from datetime import datetime

from typing import List, Dict, Any, Tuple

from domain.models.profile import Subject
from domain.models.message import Message, Role
from domain.models.response import ChatResponse

from application.services.chat_service import ChatService
from application.services.session_manager import SessionManager
from application.services.prompt_builder import PromptBuilder
from application.stateless_services.learning_service import LearningService

from domain.exceptions import (
    LLMError,
    AuthorizationError,
    SyncAndCloseSessionError,
    CompressSessionHistoryError
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
        chat_service: ChatService,
        session_manager: SessionManager,
        prompt_builder: PromptBuilder,
        learning_service: LearningService
    ):  
        # Basic service 
        self._chat_service = chat_service
        self._session_manager = session_manager
        self._prompt_builder = prompt_builder

        # Stateless service
        self._learning_service = learning_service 


    @staticmethod
    async def _if_valid_data(student_id: str, metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        # Placeholder for actual validation logic (e.g., check if user exists, session is active, etc.)
        if not metadata: 
            raise AuthorizationError("Session not found.")
        if metadata.get("student_id") != student_id:
            raise AuthorizationError("User not authorized for this session.")
        return metadata
    

    async def run(
        self,
        student_id: str,
        session_id: str,
        correlation_id: str,
        student_message: str,
        subject: Subject,
        background_task: BackgroundTasks,
        topic: str = "general",
    ):
        """Main pipeline for processing a user message and generating a chatbot response."""
        
        try:
            # 1. Look for session metadata & 2. Validate session and user data
            metadata = await self._session_manager.redis_get_metadata(session_id)
            await self._if_valid_data(metadata, student_id)

            # 3. Check if the session is active
            is_active = metadata["is_active"]
            if not is_active:
                background_task.add_task(
                    self._learning_service.sync_and_close_session,
                    student_id=student_id,
                    session_id=session_id,
                    subject=subject,
                    topic=topic,
                    metadata=metadata,
                )
                # return because if we raise an exception here, FastAPI would not execute the background task
                return ChatResponse(
                    content="This session has expired. System is syncing data and closing the session. Please start a new session to continue.",
                    usage=None,
                    correlation_id=correlation_id,
                )

            
            # 4. Find system prompt in session metadata if exists, otherwise create new system prompt then save to metadata
            system_prompt = metadata.get("system_prompt") if metadata else None
            if not system_prompt:
                system_prompt = await self._prompt_builder.chatbot_system_prompt(
                    student_id=student_id,
                    subject=subject,
                    topic=topic,
                )
                metadata["system_prompt"] = system_prompt
                await self._session_manager.redis_save_metadata(session_id, metadata)

            # 5. Compress history messages
            if metadata.get("turn_count", 0) > self.TURN_THRESHOLD:
                # msg_to_compress = await self._session_manager.redis_get_left(session_id, limit=self.TURN_TO_COMPRESS * self.MSG_PER_TURN)
                # compress_prompt = await self._prompt_builder.compress_history_prompt()

                # compress_context = await self._learning_service.compress_context(
                #     system_prompt=compress_prompt,
                #     messages=msg_to_compress,
                # )

                # await self._session_manager.redis_delete_left(session_id, limit=self.TURN_TO_COMPRESS * self.MSG_PER_TURN)

                # metadata["summary"] = metadata.get("summary", "") + "\n" + compress_context
                # metadata["turn_count"] -= self.TURN_TO_COMPRESS
                # await self._session_manager.redis_save_metadata(session_id, metadata)
                
                metadata = await self._learning_service.compress_session_history(
                    student_id=student_id,
                    session_id=session_id,
                    metadata=metadata,
                    MSG_TO_COMPRESS=self.TURN_TO_COMPRESS * self.MSG_PER_TURN,
                    TURN_TO_COMPRESS=self.TURN_TO_KEEP 
                )

            # 6. Get history messages
            history_summary = metadata.get("summary", "")
            history_messages = []
            if history_summary:
                history_messages.append(Message(
                    role=Role.SYSTEM,
                    content=history_summary,
                ))

            history_messages += await self._session_manager.redis_get_right(session_id, limit=self.TURN_TO_KEEP * self.MSG_PER_TURN)

            # 7. Build LLM input messages and call LLM to get response
            student_msg_obj = Message(
                role=Role.USER, 
                content=student_message,
                correlation_id=correlation_id,
            )
            
            llm_input_messages = history_messages + [student_msg_obj]

            llm_response = await self._chat_service.generate_response(
                system_prompt=system_prompt,
                messages=llm_input_messages,
            )

            # 8. Save user message and assistant response to session history
            llm_msg_obj = Message(
                role=Role.ASSISTANT,
                content=llm_response.content,
                correlation_id=correlation_id,
            )
            await self._session_manager.redis_save_turn(session_id, student_msg_obj, llm_msg_obj)

            # 9. Increment turn count in metadata
            metadata["turn_count"] += 1
            await self._session_manager.redis_save_metadata(session_id, metadata)

            # 10. Return response to user
            chatbot_response = ChatResponse(
                content=llm_response.content,
                usage=llm_response.usage.model_dump() if llm_response.usage else {},
                correlation_id=correlation_id,
            )

            logger.info(
                "chatbot.processing.completed",
                session_id=session_id,
                log_type="business",
                model_name=llm_response.model_name,
                usage=chatbot_response.usage,
            )

            return chatbot_response
        
        except AuthorizationError as e:
            logger.warning(
                "chatbot.authorization.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authorization failed for this session.",
            )
        
        except LLMError as e:
            logger.error(
                "chatbot.llm.response_generation.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LLM response generation failed during chatbot response generation.",
            )
        
        except SyncAndCloseSessionError as e:
            logger.error(
                "chatbot.sync_and_close_session.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync and close the session.",
            )
        
        except CompressSessionHistoryError as e:
            logger.error(
                "chatbot.compress_session_history.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to compress session history.",
            )
        
        except Exception as e:
            logger.error(
                "chatbot.unexpected.failed",
                session_id=session_id,
                log_type="technical",
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred.",
            )
        
