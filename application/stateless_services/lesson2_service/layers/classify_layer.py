from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.metadata import Lesson2ChatRequest
from domain.models.lesson2_models.classify import ClassifyInput, ClassifyOutput
from domain.models.lesson2_models.metadata import Lesson2LayerUsage

class ClassifyLayer:
    """Layer responsible for classifying the user's message and determining the appropriate response based on the content and context of the message."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(self, input: ClassifyInput) -> Lesson2LayerUsage:
        pass
        
    
        
    
    
    
    

    