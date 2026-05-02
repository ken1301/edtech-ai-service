from typing import Optional

from domain.ports.profile_store_port import ProfileStorePort
from domain.ports.session_store_port import SessionStorePort
from domain.models.profile import Subject, StudentProfile
from infrastructure.logging import logger

from application.services.docs.prompt_templates.chatbot_prompt import PROMPT_TEMPLATES
from application.services.docs.prompt_templates.summarize_prompt import SUMMARIZE_PROMPT


class PromptManager:
    """Builds context-aware system prompts from student profiles and session state."""

    def __init__(self, profile_store: ProfileStorePort, session_store: SessionStorePort):
        self.profile_store = profile_store
        self.session_store = session_store

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_student_context(profile: Optional[StudentProfile], subject: Subject, topic: str) -> str:
        if not profile:
            return (
                "Đây là học sinh mới, chưa có thông tin về điểm mạnh hay điểm yếu trong môn học này.\n"
                f"Chủ đề đang học: {subject.value} - {topic}.\n"
                "------------------------------------\n"
            )

        subject_knowledge = profile.knowledge_map.get(subject.value, {})
        other_subjects = {
            k: v for k, v in profile.knowledge_map.items() if k != subject.value
        }

        context = (
            f"Học sinh tên {profile.full_name or 'Unknown'}, lớp {profile.grade or 'N/A'}.\n"
            f"Thông tin cá nhân: {profile.preferences or {}}.\n"
            f"Chủ đề đang học: {subject.value} - {topic}.\n"
            f"Kiến thức về {subject.value}: {subject_knowledge}.\n"
            f"Kiến thức về các môn khác: {other_subjects}.\n"
            "------------------------------------\n"
        )

        logger.info("STUDENT_CONTEXT_BUILT", student_id=profile.student_id)
        return context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_chatbot_prompt(
        self,
        session_id: str,
        student_id: str,
        subject: Subject,
        topic: str = "General",
        lang: str = "vi",
    ) -> str:
        profile = await self.profile_store.get_student_profile(student_id)
        student_ctx = self._build_student_context(profile, subject, topic)

        subject_templates = PROMPT_TEMPLATES.get(lang, PROMPT_TEMPLATES.get("vi", {}))
        base_prompt = subject_templates.get(subject.value, subject_templates.get("GENERAL", ""))

        system_prompt = student_ctx + base_prompt
        logger.info("CHATBOT_PROMPT_BUILT", session_id=session_id, subject=subject.value, lang=lang)
        return system_prompt

    async def get_summarize_prompt(
        self,
        subject: Subject,
        topic: str = "General",
        lang: str = "vi",
    ) -> str:
        lang_prompts = SUMMARIZE_PROMPT.get(lang, SUMMARIZE_PROMPT.get("vi", {}))
        prompt = lang_prompts.get(subject.value, lang_prompts.get("GENERAL", ""))
        return prompt

    async def get_compression_prompt(self) -> str:
        """Returns the prompt used for context compression (Haiku / cheap model)."""
        return (
            "Bạn là trợ lý tóm tắt hội thoại. "
            "Hãy tóm tắt các tin nhắn sau thành một đoạn văn ngắn gọn (tối đa 200 từ), "
            "giữ lại những điểm kiến thức quan trọng, lỗi học sinh đã mắc và tiến trình học tập. "
            "Trả về bằng cùng ngôn ngữ với cuộc hội thoại."
        )
