from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Optional

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

    LESSON2_EXERCISE_EXTRACTION_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "lesson2_exercise_extraction.txt").read_text(encoding="utf-8")
    LESSON2_COMPRESS_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "compress.txt").read_text(encoding="utf-8")
    LESSON2_SUMMARIZE_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "summarize.txt").read_text(encoding="utf-8")

    LESSON2_CLASSIFY_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "classify.txt").read_text(encoding="utf-8")
    LESSON2_GROUND_SUBMISSION_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "ground_submission.txt").read_text(encoding="utf-8")
    LESSON2_EVALUATE_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "evaluate.txt").read_text(encoding="utf-8")
    LESSON2_DECIDE_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "decide.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_NON_LEARNING_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_non_learning.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_P_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_p.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_D_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_d.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_E_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_e.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_PHASE_O_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_phase_o.txt").read_text(encoding="utf-8")
    LESSON2_RESPOND_WRAP_UP_PROMPT = (_LESSON2_PROMPT_TEMPLATE_DIR / "respond_wrap_up.txt").read_text(encoding="utf-8")

    def __init__(self):
        pass

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

    @classmethod
    def _resolve_context_value(cls, context: Mapping[str, Any], key: str) -> Any:
        if key in context:
            return context[key]

        current: Any = context
        for part in key.split("."):
            if isinstance(current, Mapping):
                if part not in current:
                    return None
                current = current[part]
                continue

            if hasattr(current, part):
                current = getattr(current, part)
                continue

            return None

        return current

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
            value = cls._resolve_context_value(context, key)
            if value is None and key not in context:
                return match.group(0)
            return cls._serialize_value(value)

        return re.sub(r"\{\{\s*([a-zA-Z0-9_\.]+)\s*\}\}", replace, template)

    async def lesson2_classify_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_CLASSIFY_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.classify_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate classify prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.classify_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate classify prompt.") from e

    async def lesson2_ground_submission_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_GROUND_SUBMISSION_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.ground_submission_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate ground submission prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.ground_submission_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate ground submission prompt.") from e

    async def lesson2_evaluate_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_EVALUATE_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.evaluate_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate evaluate prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.evaluate_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate evaluate prompt.") from e

    async def lesson2_decide_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_DECIDE_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.decide_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate decide prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.decide_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate decide prompt.") from e

    async def lesson2_non_learning_response_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_RESPOND_NON_LEARNING_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.non_learning_response_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate non-learning response prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.non_learning_response_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate non-learning response prompt.") from e

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

        try:
            return self._render_template(template, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.response_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate response prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.response_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate response prompt.") from e


    async def lesson2_wrap_up_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_RESPOND_WRAP_UP_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.wrap_up_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate wrap-up prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.wrap_up_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate wrap-up prompt.") from e

    async def lesson2_compress_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_COMPRESS_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.compress_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate compress prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.compress_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate compress prompt.") from e

    async def lesson2_summarize_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_SUMMARIZE_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.summarize_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate summarize prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.summarize_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate summarize prompt.") from e

    async def lesson2_exercise_extraction_prompt(self, **context: Any) -> str:
        try:
            return self._render_template(self.LESSON2_EXERCISE_EXTRACTION_PROMPT, **context)
        except (ValueError, TypeError) as e:
            logger.error(
                "prompt_builder.lesson2_exercise_extraction_prompt.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate exercise extraction prompt.") from e
        except Exception as e:
            logger.error(
                "prompt_builder.lesson2_exercise_extraction_prompt.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise PromptGenerationError("Failed to generate exercise extraction prompt.") from e