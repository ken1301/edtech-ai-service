from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel

from domain.models.overall_models.message import Message
from domain.models.lesson2_models.common import SubmissionData, Lesson2LayerUsage  # noqa: F401  (re-export)


class Intent(str, Enum):
    LEARNING_DISCUSSION = "learning_discussion"
    ANSWER_STATEMENT = "answer_statement"
    OFF_TOPIC = "off_topic"
    GREETING = "greeting"
    META_QUERY = "meta_query"
    EMOTIONAL_EXPRESSION = "emotional_expression"
    GIVE_UP = "give_up"
    BACKTRACK_REQUEST = "backtrack_request"
    ANSWER_EXTRACTION = "answer_extraction"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    UNINTELLIGIBLE = "unintelligible"

class EmotionalSignal(BaseModel):
    valence: float
    frustration: float
    confusion: float
    confidence_tone: float

class Routing(str, Enum):
    FAST_PATH_REPLY = "fast_path_reply"
    FULL_PIPELINE = "full_pipeline"
    SAFETY_DIVERT = "safety_divert"

class ClassifyInput(BaseModel):
    user_msg: str
    is_submission: bool
    submission_data: Optional[SubmissionData] = None
    recent_messages: List[Message]
    current_problem_id: Optional[int] = None 
    problem_question: List[str] = [] # all questions of the problem (id from 1 to 4)

class ClassifyOutput(BaseModel):
    intent: Intent
    intent_confidence: float
    emotional: EmotionalSignal
    learning_relevance: float
    references_problem_id: Optional[int]
    abuse_flags: List[Literal["jailbreak", "extract_answer", "hostile", "spam"]]
    routing: Routing
