from pydantic import BaseModel
from typing import Optional, Dict, Any

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: Optional[float] = None

class LLMResponse(BaseModel):
    content: str
    model_name: str
    finish_reason: str
    usage: TokenUsage

class ChatResponse(BaseModel):
    content: str
    usage: Optional[Dict[str, Any]]
    correlation_id: str