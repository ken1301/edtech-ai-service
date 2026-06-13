from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.ground import GroundInput, GroundOutput
from domain.models.lesson2_models.common import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger

class GroundLayer:
    """Layer responsible for grounding the conversation in the relevant context, such as the lesson content, previous messages, and any other pertinent information that can help the model generate a more accurate and contextually appropriate response."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
         self._prompt_builder = prompt_builder
         self._llm_manager = llm_manager

    async def execute(self, input: GroundInput) -> Lesson2LayerUsage:
        try:
            logger.debug(
                "ground_layer.called",
                log_type="debug",
            )

            prompt = await self._prompt_builder.lesson2_ground_submission_prompt(**input.model_dump())
            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=[],
                response_model=GroundOutput,
            )


            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate grounding.") from e

        except Exception as e:
            logger.error(
                "ground_layer.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to ground user message.") from e
