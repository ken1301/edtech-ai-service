from typing import Optional

from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.prompt_builder import PromptBuilder

from domain.models.lesson2_models.evaluate import Phase
from domain.models.lesson2_models.response import ResponseInput
from domain.models.lesson2_models.metadata import Lesson2LayerUsage


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
        pass