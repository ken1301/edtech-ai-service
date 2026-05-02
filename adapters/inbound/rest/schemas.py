import uuid
from typing import Literal
from pydantic import BaseModel, Field

from domain.models.profile import Subject


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str = Field(..., min_length=1)
    subject: Subject
    topic: str = "General"
    lang: Literal["vi", "en"] = "vi"
    corr_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
