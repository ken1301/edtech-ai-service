from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

from domain.ports.profile_store_port import ProfileStorePort

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.profile import StudentProfile
from domain.models.lesson2_models.evaluate import Phase

from domain.exceptions import PromptGenerationError, ProfileStoreError

from infrastructure.logging import logger


class PromptBuilder:
    """Builds legacy prompts and the lesson2 prompt set from template files."""

    _BASE_DIR = Path(__file__).resolve().parent.parent / "docs"
    _LEGACY_PROMPT_TEMPLATE_DIR = _BASE_DIR / "prompt_templates"
    _LESSON2_PROMPT_TEMPLATE_DIR = _BASE_DIR / "lesson2_prompts"

    THINKING_PROMPT = (_LEGACY_PROMPT_TEMPLATE_DIR / "thinking_prompt.txt").read_text(encoding="utf-8")
    ANSWERING_PROMPT = (_LEGACY_PROMPT_TEMPLATE_DIR / "answering_prompt.txt").read_text(encoding="utf-8")
    COMPRESS_CONTEXT_PROMPT = (_LEGACY_PROMPT_TEMPLATE_DIR / "compress_context_prompt.txt").read_text(encoding="utf-8")
    SUMMARIZE_SESSION_PROMPT = (_LEGACY_PROMPT_TEMPLATE_DIR / "summarize_session_prompt.txt").read_text(encoding="utf-8")
    EXERCISE_EXTRACTION_PROMPT = (_LEGACY_PROMPT_TEMPLATE_DIR / "exercise_extraction_prompt.txt").read_text(encoding="utf-8")

    LESSON2_CLASSIFY_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "classify.txt").read_text(encoding="utf-8")
    LESSON2_GROUND_SUBMISSION_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "ground_submission.txt").read_text(encoding="utf-8")
    LESSON2_EVALUATE_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "evaluate.txt").read_text(encoding="utf-8")
    LESSON2_DECIDE_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "decide.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_NON_LEARNING_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_non_learning.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_P_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_p.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_D_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_d.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_E_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_e.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_O_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_o.txt").read_text(encoding="utf-8")

    def __init__(self, profile_store: ProfileStorePort):
        self._profile_store = profile_store

    @staticmethod
    def _serialize_value(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, Enum):
            return str(value.value)

        if hasattr(value, "model_dump"):
            value = value.model_dump()

        if isinstance(value, Mapping):
            return json.dumps(value, ensure_ascii=False, indent=2, default=PromptBuilder._json_default)

        if isinstance(value, (list, tuple, set)):
            return json.dumps(list(value), ensure_ascii=False, indent=2, default=PromptBuilder._json_default)

        return str(value)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "value"):
            return value.value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return str(value)

    @classmethod
    def _render_template(cls, template: str, **context: Any) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            if key not in context:
                return match.group(0)
            return cls._serialize_value(context[key])

        return re.sub(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}", replace, template)

    @staticmethod
    def _get_student_context(
        student_profile: StudentProfile, 
        user_id: str, 
        subject: Subject,
        topic: Topic,
        concept: Concept
    ) -> str:
        try:
            if not student_profile:
                logger.warning(
                    "prompt_builder.get_student_context.no_profile",
                    log_type="business",
                    user_id=user_id,
                )
                return (
                    "This student does not have a profile yet. No information about their mastery level, misconceptions, or preferences is available.\n"
                    f"Basic information: The student is learning {subject.value}, {topic.value}, {concept.value}."
                )

            subject_knowledge = student_profile.knowledge_map.get(subject.value, {})
            other_subjects = {key: value for key, value in student_profile.knowledge_map.items() if key != subject.value}

            return (
                f"Student name: {student_profile.full_name or 'Unknown'}, lớp {student_profile.grade or 'N/A'}.\n"
                f"Personal information: {student_profile.preferences or {}}.\n"
                f"Current topic: {subject.value} - {topic.value} - {concept.value}.\n"
                f"Knowledge about {subject.value}: {subject_knowledge}.\n"
                f"Knowledge about other subjects: {other_subjects}.\n"
            )

        except Exception as exc:
            logger.error(
                "prompt_builder.get_student_context.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                error=str(exc),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to get student context for prompt generation.") from exc

    async def chatbot_system_prompt(self, user_id: str, subject: Subject, topic: Topic, concept: Concept) -> str:
        try:
            student_profile = await self._profile_store.get_student_profile(user_id)
            system_prompt = self._get_student_context(student_profile, user_id, subject, topic, concept)
            system_prompt += "\n\n" + self.THINKING_PROMPT + "\n\n" + self.ANSWERING_PROMPT

            logger.info(
                "prompt_builder.chatbot_system_prompt.completed",
                log_type="business",
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
            )
            return system_prompt

        except ProfileStoreError as exc:
            raise PromptGenerationError("Failed to generate chatbot system prompt.") from exc
        except Exception as exc:
            logger.error(
                "prompt_builder.chatbot_system_prompt.unexpected.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject.value,
                topic=topic.value,
                concept=concept.value,
                error=str(exc),
                exc_info=True,
            )
            raise PromptGenerationError("Unexpected error during chatbot system prompt generation.") from exc

    async def summarize_session_prompt(self) -> str:
        try:
            logger.info("prompt_builder.summarize_session_prompt.completed", log_type="business")
            return self.SUMMARIZE_SESSION_PROMPT
        except Exception as exc:
            logger.error(
                "prompt_builder.summarize_session_prompt.failed",
                log_type="technical",
                error=str(exc),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate summarize session prompt.") from exc

    async def compress_history_prompt(self) -> str:
        try:
            logger.info("prompt_builder.compress_history_prompt.completed", log_type="business")
            return self.COMPRESS_CONTEXT_PROMPT
        except Exception as exc:
            logger.error(
                "prompt_builder.compress_history_prompt.failed",
                log_type="technical",
                error=str(exc),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate compress history prompt.") from exc

    async def exercise_extraction_prompt(self) -> str:
        try:
            logger.info("prompt_builder.exercise_extraction_prompt.completed", log_type="business")
            return self.EXERCISE_EXTRACTION_PROMPT
        except Exception as exc:
            logger.error(
                "prompt_builder.exercise_extraction_prompt.failed",
                log_type="technical",
                error=str(exc),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate exercise extraction prompt.") from exc

    async def lesson2_classify_prompt(self, **context: Any) -> str:
        return self._render_template(self.LESSON2_CLASSIFY_PROMPT, **context)

    async def lesson2_ground_submission_prompt(self, **context: Any) -> str:
        return self._render_template(self.LESSON2_GROUND_SUBMISSION_PROMPT, **context)

    async def lesson2_evaluate_prompt(self, **context: Any) -> str:
        return self._render_template(self.LESSON2_EVALUATE_PROMPT, **context)

    async def lesson2_decide_prompt(self, **context: Any) -> str:
        return self._render_template(self.LESSON2_DECIDE_PROMPT, **context)

    async def lesson2_non_learning_response_prompt(self, **context: Any) -> str:
        return self._render_template(self.LESSON2_RESPOND_NON_LEARNING_PROMPT, **context)

    async def lesson2_response_prompt(self, phase: Phase, **context: Any) -> str:
        phase_key = phase.value if isinstance(phase, Phase) else str(phase)
        if phase_key == Phase.PROBLEM.value:
            template = self.LESSON2_RESPOND_PHASE_P_PROMPT
        elif phase_key == Phase.DONE.value:
            template = self.LESSON2_RESPOND_PHASE_D_PROMPT
        elif phase_key == Phase.EXECUTE.value:
            template = self.LESSON2_RESPOND_PHASE_E_PROMPT
        elif phase_key == Phase.OPTIMIZE.value:
            template = self.LESSON2_RESPOND_PHASE_O_PROMPT
        else:
            raise PromptGenerationError(f"Unsupported lesson2 phase: {phase_key}")

        return self._render_template(template, **context)