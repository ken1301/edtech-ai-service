import json

from infrastructure.logging import logger

from domain.ports.session_store_port import SessionStorePort
from domain.ports.profile_store_port import ProfileStorePort
from domain.ports.llm_port import LLMPort
from domain.models.profile import Subject

from application.services.prompt_manager import PromptManager


class LearningUseCase:
    """Finalises a learning session: summarises conversation, updates student knowledge map."""

    def __init__(
        self,
        llm: LLMPort,
        profile_store: ProfileStorePort,
        session_store: SessionStorePort,
        prompt_manager: PromptManager,
    ):
        self.llm = llm
        self.profile_store = profile_store
        self.session_store = session_store
        self.prompt_manager = prompt_manager

    async def sync_and_close_session(
        self,
        student_id: str,
        session_id: str,
        subject: Subject,
        topic: str = "General",
        lang: str = "vi",
    ) -> None:
        """Summarise session, persist learning data to profile, then clear session cache."""
        history = await self.session_store.get_history(session_id)

        description = "EMPTY_HISTORY"

        if history:
            summarize_prompt = await self.prompt_manager.get_summarize_prompt(
                subject=subject,
                topic=topic,
                lang=lang,
            )

            llm_result = await self.llm.generate_response(
                system_prompt=summarize_prompt,
                messages=history,
            )

            try:
                raw = llm_result.content.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                data = json.loads(raw)
            except (ValueError, KeyError, IndexError):
                logger.warning(
                    "SUMMARIZE_PARSE_ERROR",
                    student_id=student_id,
                    session_id=session_id,
                    raw_content=llm_result.content[:200],
                )
                data = {"score": 0.0, "misconceptions": [], "summary": llm_result.content}

            await self.profile_store.update_knowledge_map(
                student_id=student_id,
                subject=subject.value,
                topic=topic,
                data=data,
            )
            description = "SUCCESS" if llm_result.content else "EMPTY_RESPONSE"

        logger.info(
            "SYNC_AND_CLOSE_SESSION",
            student_id=student_id,
            session_id=session_id,
            description=description,
        )

        await self.session_store.clear_session(session_id)
