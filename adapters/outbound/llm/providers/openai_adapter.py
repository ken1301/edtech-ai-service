import openai
from openai import AsyncOpenAI
import instructor
from pydantic import BaseModel
from typing import List, Optional

from domain.exceptions import LLMError
from domain.ports.llm_port import LLMPort
from domain.models.message import Message, ConversationContext
from domain.models.response import LLMResponse, TokenUsage

from infrastructure.logging import logger


class OpenaiAdapter(LLMPort):
    """OpenAI LLM adapter implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-5.4-nano"):
        """Initialize OpenAI adapter
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini for cost efficiency)
        """
        self.base_client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.client = instructor.from_openai(self.base_client)

    async def generate_response(
            self,
            system_prompt: str,
            messages: List[Message],
            context: Optional[ConversationContext] = None,
            response_model: Optional[BaseModel] = None
    ) -> LLMResponse:
        """Generate a response using OpenAI API
        
        Args:
            system_prompt: System instruction for the model
            messages: List of conversation messages
            context: Optional context with temperature and max tokens
            response_model: Optional response model
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
                "max_completion_tokens": max_tokens,
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
        
        except openai.RateLimitError as e:
            logger.warning(
                "openai_adapter.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("OpenAI API rate limit exceeded. Please try again later.") from e
        
        except openai.AuthenticationError as e:
            logger.error(
                "openai_adapter.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("OpenAI API authentication failed. Check your API key.") from e
        
        except openai.BadRequestError as e: 
            logger.error(
                "openai_adapter.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("OpenAI API bad request. Check your input parameters.") from e
        
        except openai.OpenAIError as e:
            logger.error(
                "openai_adapter.api_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("OpenAI API error occurred. Please try again later.") from e
        
        except Exception as e:
            logger.error(
                "openai_adapter.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMError("An unknown error occurred while calling OpenAI API.") from e

    async def generate_stream(
            self,
            messages: List[Message],
            context: Optional[ConversationContext] = None
    ):
        """Generate a streaming response from OpenAI"""
        raise NotImplementedError("Streaming support coming soon")