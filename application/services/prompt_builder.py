import json

from domain.ports.profile_store_port import ProfileStorePort

from domain.models.profile import Subject, StudentProfile

from domain.exceptions import PromptGenerationError

from infrastructure.logging import logger

class PromptBuilder:
    """Service responsible for building prompts for the LLM based on the student profile, prompt templates."""

    with open("./docs/prompt_templates/thinking_prompt.json", "r", encoding="utf-8") as f:
        THINKING_PROMPT = json.load(f)

    with open("./docs/prompt_templates/answering_prompt.json", "r", encoding="utf-8") as f:
        ANSWERING_PROMPT = json.load(f)

    with open("./docs/prompt_templates/learning_service_prompt.json", "r", encoding="utf-8") as f:
        LEARNING_SERVICE_PROMPT = json.load(f)

    def __init__(
        self,
        profile_store: ProfileStorePort
    ):
        self._profile_store = profile_store

    @staticmethod
    async def _get_student_context(
        student_profile: StudentProfile,
        student_id: str,
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
                    student_id=student_id
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
                    
        
        except Exception as e:
            logger.error(
                "prompt_builder.get_student_context.failed",
                log_type="technical",
                student_id=student_id,
                subject=subject.value,
                topic=topic,
                error=str(e),
            )
            raise PromptGenerationError("Failed to get student context for prompt generation.") from e

    async def chatbot_system_prompt(
        self,
        student_id: str,
        subject: Subject,
        topic: str,
    ) -> str:
        try:
            student_profile = await self._profile_store.get_student_profile(student_id)
            systemp_prompt = self._get_student_context(student_profile, student_id, subject, topic)

            systemp_prompt += "\n\n" + self.THINKING_PROMPT["system_prompt"] + "\n\n" + self.ANSWERING_PROMPT["system_prompt"]

            logger.info(
                "prompt_builder.chatbot_system_prompt.completed",
                log_type="business",
            )
            return systemp_prompt
        
        except Exception as e:
            logger.error(
                "prompt_builder.chatbot_system_prompt.failed",
                log_type="technical",
                error=str(e),
            )
            raise PromptGenerationError("Failed to generate chatbot system prompt.") from e
    

    async def summarize_session_prompt(self) -> str:
        try: 
            logger.info(
                "prompt_builder.summarize_session_prompt.completed",
                log_type="business",
            )
            return self.LEARNING_SERVICE_PROMPT["summarize_session_system_prompt"]
        
        except Exception as e:
            logger.error(
                "prompt_builder.summarize_session_prompt.failed",
                log_type="technical",
                error=str(e),
            )
            raise PromptGenerationError("Failed to generate summarize session prompt.") from e

    async def compress_history_prompt(self) -> str:
        try:
            logger.info(
                "prompt_builder.compress_history_prompt.completed",
                log_type="business",
            )
            return self.LEARNING_SERVICE_PROMPT["compress_history_system_prompt"]
        
        except Exception as e:
            logger.error(
                "prompt_builder.compress_history_prompt.failed",
                log_type="technical",
                error=str(e),
            )
            raise PromptGenerationError("Failed to generate compress history prompt.") from e
