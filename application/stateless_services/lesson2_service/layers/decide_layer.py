from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.decide import DecideInput, DecideOutput, ResponseDirective
from domain.models.lesson2_models.decide import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger

class DecideLayer:
    """Layer responsible for making the final decision on how to respond to the user's message, based on the output from the previous layers and any additional processing or rules that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager


    async def execute(self, input: DecideInput) -> Lesson2LayerUsage:
        try:
            prompt = await self._prompt_builder.lesson2_decide_prompt(**input.model_dump())
            logger.debug(
                "decide_layer.called",
                log_type="debug",
                session_id=input.session_id,
            )
            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=[],
                response_model=DecideOutput,
            )
            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate decision.") from e

        except Exception as e:
            logger.error(
                "decide_layer.unexpected.failed",
                log_type="error",
                session_id=input.session_id,
                error=str(e),
                exc_info=True,
            )
            raise e