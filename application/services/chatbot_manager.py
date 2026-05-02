from fastapi import BackgroundTasks

from domain.exceptions import SessionExpiredError
from domain.models.profile import Subject
from domain.models.response import ChatResponse

from application.use_cases.chat_usecase import SocraticChat
from application.use_cases.learning_usecase import LearningUseCase
from application.services.session_manager import SessionManager
from application.services.prompt_manager import PromptManager


class ChatbotManager:
    """Orchestrates a single chat turn: session lifecycle → prompt → chat → turn tracking."""

    def __init__(
        self,
        chat_use_case: SocraticChat,
        session_manager: SessionManager,
        learning_use_case: LearningUseCase,
        prompt_manager: PromptManager,
    ):
        self.chat_use_case = chat_use_case
        self.session_manager = session_manager
        self.learning_use_case = learning_use_case
        self.prompt_manager = prompt_manager

    async def handle_chat(
        self,
        student_id: str,
        session_id: str,
        subject: Subject,
        topic: str,
        user_message: str,
        corr_id: str,
        lang: str,
        background_tasks: BackgroundTasks,
    ) -> ChatResponse:
        session_meta, is_active = await self.session_manager.get_or_create_session(session_id)

        if not is_active:
            background_tasks.add_task(
                self.learning_use_case.sync_and_close_session,
                student_id=student_id,
                session_id=session_id,
                subject=subject,
                topic=topic,
                lang=lang,
            )
            raise SessionExpiredError("Session has expired. Please start a new session.")

        # Build system prompt once per session and cache it in metadata
        system_prompt = session_meta.get("system_prompt")
        if not system_prompt:
            system_prompt = await self.prompt_manager.get_chatbot_prompt(
                session_id=session_id,
                student_id=student_id,
                subject=subject,
                topic=topic,
                lang=lang,
            )
            session_meta["system_prompt"] = system_prompt
            await self.session_manager.save_metadata(session_id, session_meta)

        response = await self.chat_use_case.execute(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            corr_id=corr_id,
            session_meta=session_meta,
        )

        # Increment turn counter after each complete exchange
        await self.session_manager.increment_turn(session_id, session_meta)

        return response
