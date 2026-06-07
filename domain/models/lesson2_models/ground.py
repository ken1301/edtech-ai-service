from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from domain.models.lesson2_models.exercise import Approach


class ApproachVerdict(str, Enum):
    CORRECT = "CORRECT"
    WEAK = "WEAK"
    INCORRECT = "INCORRECT"


class GroundInput(BaseModel):
    problem_question: str
    problem_final_answer: str
    open_approach: bool
    approach_list: List[Approach]
    student_reasoning: str
    student_submitted_answer: str
    result_status: bool

    @property
    def submitted_answer(self) -> str:
        return self.student_submitted_answer

    @property
    def submission_status(self) -> bool:
        return self.result_status


class GroundOutput(BaseModel):
    result_status: bool
    approach_verdict: ApproachVerdict

    matched_approach_id: Optional[int] = None
    matched_weakness: Optional[str] = None

    judge_confidence: float
    explanation: str

    @property
    def approach_status(self) -> ApproachVerdict:
        return self.approach_verdict

    @property
    def approach_weaknesses(self) -> List[str]:
        if self.matched_weakness is None:
            return []
        return [self.matched_weakness]
