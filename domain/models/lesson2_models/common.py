from enum import Enum
from typing import Any, Tuple
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Phase(str, Enum):
    PROBLEM = "problem"
    DONE = "done"
    EXECUTE = "execute"
    OPTIMIZE = "optimize"


class DisengagementLevel(str, Enum):
    ENGAGED = "engaged"
    COASTING = "coasting"
    DISENGAGING = "disengaging"
    DISENGAGED = "disengaged"


class DistressLevel(str, Enum):
    NONE = "none"
    MILD = "mild"
    HIGH = "high"
    GIVING_UP = "giving_up"
    NON_ACADEMIC = "non_academic"


class ProcessState(str, Enum):
    WRONG_STAGNANT = "wrong_stagnant"
    WRONG_DECLINING = "wrong_declining"
    DISCOVERING = "discovering"
    IMPROVING = "improving"
    CONVERGED = "converged"


class ResponseClass(str, Enum):
    CONFIRM = "CONFIRM"
    SURFACE_WEAKNESS = "SURFACE_WEAKNESS"
    COUNTER_PERSPECTIVE = "COUNTER_PERSPECTIVE"
    GUIDE_DISCOVERY = "GUIDE_DISCOVERY"
    SOFT_INTERVENTION = "SOFT_INTERVENTION"
    APPROACH_SWITCH_WARNING = "APPROACH_SWITCH_WARNING"
    REDIRECT_TO_SUBMIT = "REDIRECT_TO_SUBMIT"
    PROBE_INTERMEDIATE_PHASE = "PROBE_INTERMEDIATE_PHASE"
    META_REPLY = "META_REPLY"
    EMPATHY = "EMPATHY"
    REFUSE_ANSWER_REQ = "REFUSE_ANSWER_REQ"
    SAFETY_HANDOFF = "SAFETY_HANDOFF"
    WRAP_UP = "WRAP_UP"


class SubmissionData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: bool
    is_progress_farm: Tuple[bool, int] = Field(
        validation_alias=AliasChoices("is_progress_farm", "is_progress_farming"),
        serialization_alias="is_progress_farming",
    )


class Lesson2LayerUsage(BaseModel):
    """Envelope returned by every lesson 2 layer: the layer's schema output plus token usage.

    Defined here (no model dependencies) so every layer/model module can re-export it
    without creating import cycles.
    """
    output: Any = None
    usage: Any = None
