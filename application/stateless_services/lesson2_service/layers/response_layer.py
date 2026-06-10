from typing import Optional

from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.prompt_builder import PromptBuilder

from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.evaluate import Phase
from domain.models.lesson2_models.response import ResponseInput
from domain.models.lesson2_models.response import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger


class ResponseLayer:
    """Layer responsible for generating the final response to be sent back to the user, based on the output from the previous layers and any additional processing or formatting that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(
        self, 
        input: ResponseInput, 
        phase: Optional[Phase] = None
    ) -> Lesson2LayerUsage:
        try:
            logger.debug(
                "response_layer.called",
                log_type="debug",
                phase=phase.value if phase else None,
            )

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate response.") from e

        except Exception as e:
            logger.error(
                "response_layer.unexpected.failed",
                log_type="error",
                session_id=input.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to generate response.") from e

