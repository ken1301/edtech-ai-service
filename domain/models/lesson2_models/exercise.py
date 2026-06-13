from pydantic import BaseModel
from typing import List, Dict, Optional

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.common import (
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

    max_attempts: int


class Problem(BaseModel):
    problem_id: int
    question: str
    attachment_url: List[str] = [] # image URLs or other resource links

    approach_list: List[Approach]
    final_answer: str

    open_approach: bool
    recommended_problem_role: ProblemRole

    max_approach_trial: int


class Exercise(BaseModel):
    problem_list: List[Problem]

    subject: Subject
    topic: Topic
    concept: Concept

    user_id: Optional[str] = None

class Lesson2Exercises(BaseModel):
    problem_set: Dict[ProblemRole, List[Problem]]
