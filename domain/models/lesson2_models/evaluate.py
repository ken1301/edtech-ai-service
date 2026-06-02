from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Literal

from domain.models.lesson2_models.metadata import SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput

class Phase(str, Enum):
    PROBLEM = "problem"
    DONE = "done"
    EXECUTE = "execute"
    OPTIMIZE = "optimize"

class EvaluateInput(BaseModel):
    classify_output: ClassifyOutput
    ground_output: Optional[GroundOutput] = None
    session_metadata: SessionMetadata

class EvaluateApproach(BaseModel):
    pass

class Misconception(BaseModel):
    pass

class EvaluateOutput(BaseModel):
    # Phase
    current_phase: Phase
    history_phase: List[Phase]
    phase_confidence: float

    # Approach 
    current_approach_id: int
    history_approaches: List[EvaluateApproach]

    # Misconceptions
    current_misconceptions: List[Misconception]
    history_misconceptions: List[Misconception]


