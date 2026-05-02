from openai import AsyncOpenAI
from typing import List, Optional

from domain.ports.llm_port import LLMPort
from domain.models.message import Message, ConversationContext
from domain.models.response import LLMResponse, TokenUsage


class OpenaiAdapter(LLMPort):
    """OpenAI LLM adapter implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize OpenAI adapter
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-mini for cost efficiency)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(
            self,
            system_prompt: str,
            messages: List[Message],
            context: Optional[ConversationContext] = None
    ) -> LLMResponse:
        """Generate a response using OpenAI API
        
        Args:
            system_prompt: System instruction for the model
            messages: List of conversation messages
            context: Optional context with temperature and max tokens
            
        Returns:
            LLMResponse with content and token usage
        """
        formatted_messages = [{"role": "system", "content": system_prompt}]

        for m in messages:
            formatted_messages.append({"role": m.role.value, "content": m.content})

        max_tokens = context.max_completion_tokens if context else None

        api_params = {
            "model": self.model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
        }

        response = await self.client.chat.completions.create(**api_params)

        return LLMResponse(
            content=response.choices[0].message.content,
            model_name=self.model,
            finish_reason=response.choices[0].finish_reason,
            usage=TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        )

    async def generate_stream(
            self,
            messages: List[Message],
            context: Optional[ConversationContext] = None
    ):
        """Generate a streaming response from OpenAI
        
        TODO: Implement streaming response support
        """
        raise NotImplementedError("Streaming support coming soon")