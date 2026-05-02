from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.message import Message, ConversationContext
from domain.models.response import LLMResponse


class LLMPort(ABC):
    """Abstract port for LLM providers"""
    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Message],
        context: Optional[ConversationContext] = None
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        context: Optional[ConversationContext] = None
    ):
        """Generate a streaming response from the LLM"""
        pass
