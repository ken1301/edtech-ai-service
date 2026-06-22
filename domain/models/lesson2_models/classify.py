from enum import Enum
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints

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


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]

class EmotionalSignal(BaseModel):
    valence: float = Field(ge=0.0, le=1.0)
    frustration: float = Field(ge=0.0, le=1.0)
    confusion: float = Field(ge=0.0, le=1.0)
    confidence_tone: float = Field(ge=0.0, le=1.0)

class Routing(str, Enum):
    FAST_PATH_REPLY = "fast_path_reply"
    FULL_PIPELINE = "full_pipeline"
    SAFETY_DIVERT = "safety_divert"

class ClassifyInput(BaseModel):
    is_submission: bool
    submission_data: Optional[SubmissionData] = None
    recent_messages: List[Message] = Field(default_factory=list, max_length=12)
    current_problem_id: Optional[int] = Field(default=None, gt=0)
    problem_question: List[ShortText] = Field(default_factory=list, max_length=8) # all questions of the problem (id from 1 to 4)

class ClassifyOutput(BaseModel):
    intent: Intent
    intent_confidence: float = Field(ge=0.0, le=1.0)
    emotional: EmotionalSignal
    learning_relevance: float = Field(ge=0.0, le=1.0)
    references_problem_id: Optional[int] = Field(default=None, gt=0)
    abuse_flags: List[Literal["jailbreak", "extract_answer", "hostile", "spam"]] = Field(default_factory=list, max_length=4)
    routing: Routing
