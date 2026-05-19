from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
from domain.models.standard import Role

class Message(BaseModel):
    role: Role
    content: str

    correlation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}

class ConversationContext(BaseModel):
    temperature: float = 0.3
    max_completion_tokens: Optional[int] = None
    stream: bool = False
