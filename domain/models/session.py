from pydantic import BaseModel
from typing import List, Dict, Any

from domain.models.message import Message

class ChatSession(BaseModel):
    student_id: str
    session_id: str
    messages: List[Message] = []

    metadata: Dict[str, Any] = {}
