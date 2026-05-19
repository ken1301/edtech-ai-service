from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime, timezone

from domain.models.message import Message
from domain.models.profile import StudentPreference, TopicMastery

from domain.models.standard import Subject, Topic

class SessionMetadata(BaseModel):
    subject: Subject
    topic: Topic
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    summary: str
    system_prompt: str


class ChatSession(BaseModel):
    user_id: str
    session_id: str
    messages: List[Message] = []

    metadata: SessionMetadata
    

class SessionSummary(BaseModel):
    student_preference: StudentPreference
    topic_mastery: TopicMastery