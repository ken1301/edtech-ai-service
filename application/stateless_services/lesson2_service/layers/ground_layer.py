from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.ground import GroundInput, GroundOutput
from domain.models.lesson2_models.ground import Lesson2LayerUsage

class GroundLayer:
    """Layer responsible for grounding the conversation in the relevant context, such as the lesson content, previous messages, and any other pertinent information that can help the model generate a more accurate and contextually appropriate response."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
         self._prompt_builder = prompt_builder
         self._llm_manager = llm_manager

    async def execute(self, input: GroundInput) -> Lesson2LayerUsage:
        pass