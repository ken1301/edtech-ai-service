from typing import Optional
from pydantic import BaseModel

from domain.ports.llm_port import LLMPort

from domain.models.response import LLMResponse
from domain.models.message import Message, ConversationContext

from infrastructure.logging import logger

from domain.exceptions import LLMError

class ChatService:
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
                "llm.generate_response.completed",
                log_type="business",
            )

            return llm_response

        # some specific exceptions can be caught and re-raised as LLMError for better error handling in the use case layer

        except Exception as e:
            logger.error(
                "llm.unexpected.failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("Failed to generate response from LLM.") from e
        


