from typing import List, Optional
from pydantic import BaseModel

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import ProblemRole
from domain.models.overall_models.response import TokenUsage
from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.evaluate import EvaluateOutput
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.decide import ResponseDirective


class ResponseInput(BaseModel):
    problem_question: str
    problem_role: ProblemRole
    response_directive: ResponseDirective
    msg: str
    recent_messages: List[Message]

    classify: Optional[ClassifyOutput] = None
    evaluate: Optional[EvaluateOutput] = None
    ground_output_if_submission: Optional[GroundOutput] = None
    current_problem_index: Optional[int] = None
    is_submission: bool = False

    @property
    def student_message(self) -> str:
        return self.msg

    @property
    def ground_output(self) -> Optional[GroundOutput]:
        return self.ground_output_if_submission


class ProblemResponseInput(ResponseInput):
    pass


class DoneResponseInput(ResponseInput):
    pass


class ExecuteResponseInput(ResponseInput):
    pass


class OptimizeResponseInput(ResponseInput):
    pass


class FastResponseInput(ResponseInput):
    pass


class SafetyResponseInput(ResponseInput):
    pass


class Lesson2LayerUsage(BaseModel):
    output: ClassifyOutput | GroundOutput | EvaluateOutput | str
    usage: TokenUsage
