from groq import AsyncGroq
import groq
import instructor
from typing import List, Optional
from pydantic import BaseModel

from domain.ports.llm_port import LLMPort
from domain.models.message import Message, ConversationContext
from domain.models.response import LLMResponse, TokenUsage

from domain.exceptions import LLMError

from infrastructure.logging import logger


class GroqAdapter(LLMPort):
    """Groq LLM adapter implementation - fast inference with Llama models"""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        """Initialize Groq adapter
        
        Args:
            api_key: Groq API key
            model: Model name (default: llama-3.1-8b-instant for speed)
        """
        self.base_client = AsyncGroq(api_key=api_key)
        self.model = model
        self.client = instructor.from_groq(self.base_client)

    async def generate_response(
            self,
            system_prompt: str,
            messages: List[Message],
            context: Optional[ConversationContext] = None,
            response_model: Optional[BaseModel] = None
    ) -> LLMResponse:
        """Generate a response using Groq API
        
        Args:
            system_prompt: System instruction for the model
            messages: List of conversation messages
            context: Optional context with temperature and max tokens
            response_model: Optional Pydantic model to parse the response into
        Returns:
            LLMResponse with content and token usage
        """
        try: 
            formatted_messages = [{"role": "system", "content": system_prompt}]

            for m in messages:
                formatted_messages.append({"role": m.role.value, "content": m.content})

            temperature = context.temperature if context else 0.3
            max_tokens = context.max_completion_tokens if context else None

            api_params = {
                "model": self.model,
                "messages": formatted_messages,
                "max_tokens": max_tokens,
                "response_model": response_model,
                "temperature": temperature
            }

            response, completion = await self.client.chat.completions.create_with_completion(**api_params)

            return LLMResponse(
                content=response,
                model_name=completion.model,
                finish_reason=completion.choices[0].finish_reason,
                usage=TokenUsage(
                    prompt_tokens=completion.usage.prompt_tokens,
                    completion_tokens=completion.usage.completion_tokens,
                    total_tokens=completion.usage.total_tokens
                )
            )
        
        except groq.RateLimitError as e:
            logger.warning(
                "groq_adapter.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("Groq API rate limit exceeded. Please try again later.") from e
        
        except groq.AuthenticationError as e:
            logger.error(
                "groq_adapter.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("Groq API authentication failed. Check your API key.") from e
        
        except groq.BadRequestError as e:
            logger.error(
                "groq_adapter.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("Groq API bad request. Check your input parameters.") from e
        
        except groq.NotFoundError as e:
            logger.error(
                "groq_adapter.not_found",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("Groq API endpoint not found. Check your model name.") from e
        
        except Exception as e:
            logger.error(
                "groq_adapter.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("An unknown error occurred while communicating with the Groq API.") from e

    async def generate_stream(
            self,
            messages: List[Message],
            context: Optional[ConversationContext] = None
    ):
        """Generate a streaming response from Groq
        
        TODO: Implement streaming response support
        """
        raise NotImplementedError("Streaming support coming soon")