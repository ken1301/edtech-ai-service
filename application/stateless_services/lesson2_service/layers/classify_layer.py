from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.classify import ClassifyInput, ClassifyOutput
from domain.models.lesson2_models.common import Lesson2LayerUsage

from domain.exceptions import Lesson2LayerError, LLMManagerError

from infrastructure.logging import logger

class ClassifyLayer:
    """Layer responsible for classifying the user's message and determining the appropriate response based on the content and context of the message."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(self, input: ClassifyInput) -> Lesson2LayerUsage:
        try:
            logger.debug(
                "classify_layer.called",
                log_type="debug",
            )

            prompt = await self._prompt_builder.lesson2_classify_prompt(**input.model_dump())

            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=input.recent_messages,
                response_model=ClassifyOutput,
            )

            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate classification.") from e

        except Exception as e:
            logger.error(
                "classify_layer.unexpected.failed",
                log_type="error",
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to classify user message.") from e
    
        
    
    
    
    

    