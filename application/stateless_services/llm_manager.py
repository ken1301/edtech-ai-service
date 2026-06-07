from typing import Optional
from pydantic import BaseModel

from domain.ports.llm_port import LLMPort

from domain.models.overall_models.response import LLMResponse
from domain.models.overall_models.message import Message, ConversationContext

from infrastructure.logging import logger

from domain.exceptions import LLMAdapterError, LLMManagerError

class LLMManager:
    """Service responsible for handling chat-related operations, such as generating chatbot responses and managing conversation context."""

    def __init__(self, llm_port: LLMPort):
        self._llm_port = llm_port

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[Message],
        conversation_context: Optional[ConversationContext] = None,
        response_model: Optional[BaseModel] = None
    ) -> LLMResponse:
        """Generate a chatbot response based on the conversation history and context."""
        try: 
            llm_response = await self._llm_port.generate_response(
                system_prompt=system_prompt,
                messages=messages,
                context=conversation_context,
                response_model=response_model
            )
            
            logger.info(
                "llm_manager.generate_response.completed",
                log_type="business",
                model_name=llm_response.model_name,
            )

            return llm_response
        
        except LLMAdapterError as e:
            raise LLMManagerError("Failed to generate chatbot response from LLM.") from e

        # some specific exceptions can be caught and re-raised as LLMAdapterError for better error handling in the use case layer

        except Exception as e:
            logger.error(
                "llm_manager.generate_response.unexpected.failed",
                log_type="technical",
                error=str(e),
                exc_info=True,
            )
            raise LLMManagerError("Failed to generate response from LLM.") from e
        


