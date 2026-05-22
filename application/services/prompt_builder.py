from pathlib import Path

from domain.ports.profile_store_port import ProfileStorePort

from domain.models.curriculum import Subject
from domain.models.profile import StudentProfile

from domain.exceptions import PromptGenerationError, ProfileStoreError

from infrastructure.logging import logger

class PromptBuilder:
    """Service responsible for building prompts for the LLM based on the student profile, prompt templates."""

    _PROMPT_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "docs" / "prompt_templates"

    with open(_PROMPT_TEMPLATE_DIR / "thinking_prompt.txt", "r", encoding="utf-8") as f:
        THINKING_PROMPT = f.read()

    with open(_PROMPT_TEMPLATE_DIR / "answering_prompt.txt", "r", encoding="utf-8") as f:
        ANSWERING_PROMPT = f.read()

    with open(_PROMPT_TEMPLATE_DIR / "compress_context_prompt.txt", "r", encoding="utf-8") as f:
        COMPRESS_CONTEXT_PROMPT = f.read()

    with open(_PROMPT_TEMPLATE_DIR / "summarize_session_prompt.txt", "r", encoding="utf-8") as f:
        SUMMARIZE_SESSION_PROMPT = f.read()

    with open(_PROMPT_TEMPLATE_DIR / "exercise_extraction_prompt.txt", "r", encoding="utf-8") as f:
        EXERCISE_EXTRACTION_PROMPT = f.read()

    def __init__(
        self,
        profile_store: ProfileStorePort
    ):
        self._profile_store = profile_store

    @staticmethod
    def _get_student_context(
        student_profile: StudentProfile,
        user_id: str,
        subject: Subject,
        topic: str
    ) -> str:
        # Find student profile from the profile store (MongoDB) and extract relevant context for the prompt (e.g., mastery level, misconceptions, preferences, etc.)
        try:
            context = ""
            if not student_profile:
                context = (
                    "This student does not have a profile yet. No information about their mastery level, misconceptions, or preferences is available.\n"
                    f"Basic information: The student is learning {subject.value} on the topic of {topic}."
                )

                logger.warning(
                    "prompt_builder.get_student_context.no_profile",
                    log_type="business",
                    user_id=user_id
                )

                return context
            
            # If student profile exists, extract relevant information for the prompt
            subject_knowledge = student_profile.knowledge_map.get(subject.value, {})
            other_subjects = {
                k: v for k, v in student_profile.knowledge_map.items() if k != subject.value
            }

            context = (
                f"Student name: {student_profile.full_name or 'Unknown'}, lớp {student_profile.grade or 'N/A'}.\n"
                f"Personal information: {student_profile.preferences or {}}.\n"
                f"Current topic: {subject.value} - {topic}.\n"
                f"Knowledge about {subject.value}: {subject_knowledge}.\n"
                f"Knowledge about other subjects: {other_subjects}.\n"
            )

            return context
                    
        
        except Exception as e:
            logger.error(
                "prompt_builder.get_student_context.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject.value,
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to get student context for prompt generation.") from e

    async def chatbot_system_prompt(
        self,
        user_id: str,
        subject: Subject,
        topic: str,
    ) -> str:
        try:
            student_profile = await self._profile_store.get_student_profile(user_id)
            system_prompt = self._get_student_context(student_profile, user_id, subject, topic)

            system_prompt += "\n\n" + self.THINKING_PROMPT + "\n\n" + self.ANSWERING_PROMPT

            logger.info(
                "prompt_builder.chatbot_system_prompt.completed",
                log_type="business",
                user_id=user_id,
                subject=subject.value,
                topic=topic,
            )
            return system_prompt
        
        except ProfileStoreError as e:
            raise PromptGenerationError("Failed to generate chatbot system prompt.") from e
        
        except Exception as e:
            logger.error(
                "prompt_builder.chatbot_system_prompt.unexpected.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject.value,
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Unexpected error during chatbot system prompt generation.") from e

    async def summarize_session_prompt(self) -> str:
        try: 
            logger.info(
                "prompt_builder.summarize_session_prompt.completed",
                log_type="business",
            )
            return self.SUMMARIZE_SESSION_PROMPT
        
        except Exception as e:
            logger.error(
                "prompt_builder.summarize_session_prompt.failed",
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate summarize session prompt.") from e

    async def compress_history_prompt(self) -> str:
        try:
            logger.info(
                "prompt_builder.compress_history_prompt.completed",
                log_type="business",
            )
            return self.COMPRESS_CONTEXT_PROMPT
        
        except Exception as e:
            logger.error(
                "prompt_builder.compress_history_prompt.failed",
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate compress history prompt.") from e


    async def exercise_extraction_prompt(self) -> str:
        try:
            logger.info(
                "prompt_builder.exercise_extraction_prompt.completed",
                log_type="business",
            )
            return self.EXERCISE_EXTRACTION_PROMPT
        
        except Exception as e:
            logger.error(
                "prompt_builder.exercise_extraction_prompt.failed",
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate exercise extraction prompt.") from e