from typing import Optional

from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.prompt_builder import PromptBuilder

from domain.models.lesson2_models.common import Phase, ResponseClass, Lesson2LayerUsage
from domain.models.lesson2_models.response import ResponseInput

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger


class ResponseLayer:
    """Generates the student-facing text. Prompt selection is deterministic: safety, non-learning,
    and wrap-up have dedicated prompts; everything else uses the phase prompt (P/D/E/O). The
    ResponseDirective (class + tone + must_not_reveal) is rendered into the prompt as guardrails."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(
        self,
        input: ResponseInput,
        phase: Optional[Phase] = None,
    ) -> Lesson2LayerUsage:
        try:
            response_class = input.response_directive.response_class
            logger.debug(
                "response_layer.called",
                log_type="debug",
                phase=phase.value if phase else None,
                response_class=response_class.value,
            )

            context = input.model_dump()
            prompt = await self._select_prompt(response_class, phase or input.phase, context)

            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=input.recent_messages,
            )

            content = llm_response.content
            content = content if isinstance(content, str) else str(content)
            return Lesson2LayerUsage(output=content, usage=llm_response.usage)

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate response.") from e

        except Exception as e:
            logger.error(
                "response_layer.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to generate response.") from e

    async def _select_prompt(self, response_class: ResponseClass, phase: Optional[Phase], context: dict) -> str:
        if response_class in (ResponseClass.SAFETY_HANDOFF, ResponseClass.REFUSE_ANSWER_REQ, ResponseClass.META_REPLY, ResponseClass.EMPATHY):
            return await self._prompt_builder.lesson2_non_learning_response_prompt(**context)
        if response_class == ResponseClass.WRAP_UP:
            return await self._prompt_builder.lesson2_wrap_up_prompt(**context)
        # learning turn -> phase-specific prompt (P/D/E/O)
        return await self._prompt_builder.lesson2_response_prompt(phase=phase or Phase.PROBLEM, **context)
