from typing import Optional

from domain.ports.cache_port import CachePort
from domain.ports.db_port import MongoPort

from infrastructure.logging import logger

from domain.models.profile import Subject, StudentProfile

from application.services.docs.prompt_templates.chatbot_prompt import PROMPT_TEMPLATES
from application.services.docs.prompt_templates.summarize_prompt import SUMMARIZE_PROMPT

class PromptManager:
    """
    Manages the construction of system prompts base on session metadata and student profiles. Responsible for generating context-aware prompts for the LLM based on the current state of the session and the student's learning history.
    """

    def __init__(self, db_gateway: MongoPort, cache_gateway: CachePort):
        self.db = db_gateway
        self.cache = cache_gateway

    @staticmethod
    def _get_student_context(student_profile: StudentProfile, subject: Subject, topic: str) -> str:
        if not student_profile:
            return "Đây là học sinh mới, chưa có thông tin về điểm mạnh hay điểm yếu trong môn học này."
        
        student_name = student_profile.full_name or "student"
        grade = student_profile.grade or "unknown grade"
        student_preferences = student_profile.preferences or {}
        
        subject_knowledge = student_profile.knowledge_map.get(subject.value, {})

        another_subjects = {}
        for element in student_profile.knowledge_map:
            if element.key() != subject.value:
                another_subjects[element.key()] = student_profile.knowledge_map[element.key()]
        
        context = (
            f"Học sinh tên {student_name}, lớp {grade}. "
            f"Thông tin cá nhân: {student_preferences}. "
            f"Chủ đề đang học: {subject.value} - {topic}. "
            f"Kiến thức về {subject.value}: {subject_knowledge}. "
            f"Kiến thức về các môn khác: {another_subjects}."
            "------------------------------------\n"
        )

        logger.info(
            "STUDENT_CONTEXT_GENERATED",
            student_id=student_profile.student_id,
        )

        return context


    async def get_chatbot_prompt(self, session_id: str, student_id: str, subject: Subject, topic: str = "General", lang: str = "vi") -> str:
        """Generate a system prompt for chatbot"""
        student_profile = await self.db.get_student_profile(student_id)
        system_prompt = self._get_student_context(student_profile, subject, topic) + PROMPT_TEMPLATES.get(lang, {}).get(subject.value, SUMMARIZE_PROMPT["General"])
        logger.info("CHATBOT_PROMPT_GENERATED", session_id=session_id)
        return system_prompt

    async def get_summarize_prompt(self, session_id: str, subject: Subject, topic: str = "General", lang: str = "vi") -> str:
        """Generate a prompt for summarization"""
        logger.info("SUMMARIZE_PROMPT_GENERATED", session_id=session_id)
        return SUMMARIZE_PROMPT.get(lang, {}).get(subject.value, SUMMARIZE_PROMPT["General"])
