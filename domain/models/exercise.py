from pydantic import BaseModel, field_validator
from typing import List, Dict, Optional

from domain.models.curriculum import Subject, Topic, Concept

from domain.models.standard import (
    CognitiveOperation, 
    Representation, 
    Constraint, 
    BloomLevel, 
    ApproachStrength, 
    ApproachWeakness,
    ProblemRole,
    ConceptType
)

class ExercisePattern(BaseModel):
    cognitive_operation: List[CognitiveOperation]
    representation: List[Representation]
    constraints: List[Constraint]

class Approach(BaseModel):
    summary: str

    bloom_level: BloomLevel

    concept_type_used: List[ConceptType]
    pattern: ExercisePattern

    approach_answer: str  

    strengths: List[ApproachStrength]
    weaknesses: List[ApproachWeakness]
    

class Problem(BaseModel):
    problem_id: int # (1, 2, 3, ...) unique identifier for the problem within an exercise
    question: str
    attachment_url: Optional[str] = None  # URL đến hình ảnh, video, hoặc tài liệu liên quan

    approach_list: List[Approach]
    final_answer: str

    open_approach: bool  # Nếu True, học sinh có thể tự do chọn cách tiếp cận thay vì theo pattern đã định sẵn
    problem_role: ProblemRole

class Exercise(BaseModel):
    problem_list: List[Problem]

    subject: Subject
    topic: Topic
    concept: Concept

    # is_standard: bool

    # @field_validator("is_standard")
    # def validate_is_standard(cls, v):
    #     if not v:
    #         raise ValueError("The exercise is not qualified to use. Only exercises that meet the standard criteria can be saved.")
    #     return v
    

class ExerciseForPurpose(BaseModel):
    problem_set: Dict[ProblemRole, List[Problem]]

    # set max_approaches_per_problem and max_attemps_per_approach to guide the adaptive learning service in selecting exercises with appropriate complexity for the student