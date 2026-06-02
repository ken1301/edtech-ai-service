from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Literal

from domain.models.message import Message
from domain.models.lesson2_models.metadata import SubmissionData

class ClassifyInput(BaseModel):
    msg: str
    is_submission: bool
    submission_data: Optional[SubmissionData] = None
    recent_messages: List[Message]  # last 5 messages in the conversation, for context


class Intent(str, Enum):
    LEARNING_DISCUSSION   = "learning_discussion"
    ANSWER_STATEMENT      = "answer_statement"      # answer in chat, not submitted
    OFF_TOPIC             = "off_topic"
    GREETING              = "greeting"
    META_QUERY            = "meta_query"            # about lesson/UI/progress
    EMOTIONAL_EXPRESSION  = "emotional_expression"
    GIVE_UP               = "give_up"
    BACKTRACK_REQUEST     = "backtrack_request"     # "can we go back to P1?"
    ANSWER_EXTRACTION     = "answer_extraction"     # "just tell me"
    JAILBREAK_ATTEMPT     = "jailbreak_attempt"
    UNINTELLIGIBLE        = "unintelligible"

class EmotionalSignal(BaseModel):
    valence: float        # -1..1
    frustration: float    # 0..1
    confusion: float      # 0..1
    confidence_tone: float  # 0..1 — how confident the message sounds

class Routing(str, Enum):
    FAST_PATH_REPLY = "fast_path_reply"
    FULL_PIPELINE   = "full_pipeline"
    SAFETY_DIVERT   = "safety_divert"  # distress, non-academic emergency

class ClassifyOutput(BaseModel):
    intent: Intent
    intent_confidence: float
    emotional: EmotionalSignal
    learning_relevance: float        # 0..1
    references_problem_id: Optional[int]  # student talking about a non-current problem
    language: str                    # ISO code
    code_switching: bool
    abuse_flags: List[Literal["jailbreak","extract_answer","hostile","spam"]]
    routing: Routing