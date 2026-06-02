from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

from domain.models.exercise import Approach

class GroundInput(BaseModel):
    problem_question: str
    problem_final_answer: str
    submitted_answer: str
    submission_status: bool

    approach_list: List[Approach]
    student_reasoning: str

class ApproachStatus(str, Enum):
    CORRECT = "correct"
    WEAK = "weak"
    INCORRECT = "incorrect"

class GroundOutput(BaseModel):
    result_status: bool
    approach_status: ApproachStatus

    matched_approach_id: Optional[int] = None
    approach_weaknesses: Optional[List[str]] = []

    judge_confidence: float
    explanation: str






