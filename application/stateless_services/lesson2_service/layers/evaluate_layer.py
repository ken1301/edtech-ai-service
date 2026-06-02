from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.evaluate import EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.metadata import Lesson2LayerUsage

class EvaluateLayer:
    """Layer responsible for evaluating the output from the previous layers and determining the appropriate response based on the content and context of the message, as well as any additional processing or rules that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(self, input: EvaluateInput) -> Lesson2LayerUsage:
        pass