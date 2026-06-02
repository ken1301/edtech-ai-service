from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Literal

class DecideInput(BaseModel):
    pass

class ResponseClass(str, Enum):
    CONFIRM              = "confirm"
    SURFACE_WEAKNESS     = "surface_weakness"
    COUNTER_PERSPECTIVE  = "counter_perspective"   # bot disagrees as a peer
    GUIDE_DISCOVERY      = "guide_discovery"       # Socratic
    SOFT_INTERVENTION    = "soft_intervention"     # attempt-4 hint
    REDIRECT_TO_PROBLEM  = "redirect_to_problem"
    ADVANCE              = "advance"
    WRAP_UP              = "wrap_up"
    EMPATHY              = "empathy"
    REFUSE_ANSWER_REQ    = "refuse_answer_request"
    META_REPLY           = "meta_reply"            # UI/lesson question
    SAFETY_HANDOFF       = "safety_handoff"

class ResponseDirective(BaseModel):
    response_class: ResponseClass
    
class DecideOutput(BaseModel):
    directive: ResponseDirective
    advance_to_problem: Optional[int]
    tone: Literal["peer","peer_soft","empathetic","firm"]
    depth: Literal["one_line","short","medium"]
    must_not_reveal: List[str]  # final_answer hash, key step ids
    rationale: str