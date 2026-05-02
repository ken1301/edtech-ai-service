from typing import Literal, Optional

from domain.ports.llm_port import LLMPort
from adapters.outbound.llm.providers.groq_adapter import GroqAdapter
from adapters.outbound.llm.providers.openai_adapter import OpenaiAdapter


def llm_factory(
    provider: Literal["groq", "openai"],
    api_key: str,
    model_name: Optional[str] = None,
) -> LLMPort:
    provider = provider.lower()

    if provider == "groq":
        return GroqAdapter(api_key=api_key, model=model_name or "llama-3.1-8b-instant")

    if provider == "openai":
        return OpenaiAdapter(api_key=api_key, model=model_name or "gpt-4o-mini")

    raise ValueError(f"Unsupported LLM provider: {provider}")
