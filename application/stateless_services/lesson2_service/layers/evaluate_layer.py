from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.evaluate import EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.evaluate import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger

class EvaluateLayer:
    """Layer responsible for evaluating the output from the previous layers and determining the appropriate response based on the content and context of the message, as well as any additional processing or rules that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(self, input: EvaluateInput) -> Lesson2LayerUsage:
        try:
            prompt = await self._prompt_builder.lesson2_evaluate_prompt(**input.model_dump())
            logger.debug(
                "evaluate_layer.called",
                log_type="debug",
                session_id=input.session_id,
            )
            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=input.recent_messages,
                response_model=EvaluateOutput,
            )
            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate evaluation.") from e

        except Exception as e:
            logger.error(
                "evaluate_layer.unexpected.failed",
                log_type="error",
                session_id=input.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to evaluate user message.") from e