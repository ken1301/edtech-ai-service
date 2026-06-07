from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.decide import DecideInput, DecideOutput, ResponseDirective
from domain.models.lesson2_models.decide import Lesson2LayerUsage

class DecideLayer:
    """Layer responsible for making the final decision on how to respond to the user's message, based on the output from the previous layers and any additional processing or rules that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager


    async def execute(self, input: DecideInput) -> Lesson2LayerUsage:
        pass