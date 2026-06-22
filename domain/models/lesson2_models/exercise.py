from typing import ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

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
    summary: str = Field(min_length=1)

    bloom_level: BloomLevel

    concept_type_used: List[ConceptType]
    pattern: ExercisePattern

    approach_answer: str = Field(min_length=1)

    strengths: List[ApproachStrength]
    weaknesses: List[ApproachWeakness]

    max_attempts: int = Field(ge=1)


class Problem(BaseModel):
    problem_id: int = Field(gt=0)
    question: str = Field(min_length=1)
    attachment_url: List[str] = Field(default_factory=list) # image URLs or other resource links

    approach_list: List[Approach] = Field(min_length=1)
    final_answer: str = Field(min_length=1)

    open_approach: bool
    recommended_problem_role: ProblemRole

    max_approach_trial: int = Field(ge=1)


ROLE_ORDER: tuple[ProblemRole, ...] = (
    ProblemRole.REINFORCEMENT,
    ProblemRole.CHALLENGE,
    ProblemRole.EXPLORATION,
    ProblemRole.EXTENSION,
)

CANDIDATE_POOL_MIN_SIZE = 8


class Exercise(BaseModel):
    problem_list: List[Problem] = Field(min_length=CANDIDATE_POOL_MIN_SIZE)

    subject: Subject
    topic: Topic
    concept: Concept

    user_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_problem_pool(self) -> "Exercise":
        problem_ids = [problem.problem_id for problem in self.problem_list]
        if len(problem_ids) != len(set(problem_ids)):
            raise ValueError("problem_list must contain unique problem_id values")

        available_roles = {problem.recommended_problem_role for problem in self.problem_list}
        missing_roles = [role.value for role in ROLE_ORDER if role not in available_roles]
        if missing_roles:
            raise ValueError(
                "problem_list must cover every lesson 2 role at least once: "
                + ", ".join(missing_roles)
            )

        return self

class Lesson2Exercises(BaseModel):
    role_order: ClassVar[tuple[ProblemRole, ...]] = ROLE_ORDER
    problem_set: Dict[ProblemRole, List[Problem]]

    @model_validator(mode="after")
    def validate_problem_set(self) -> "Lesson2Exercises":
        missing_roles = [role.value for role in self.role_order if role not in self.problem_set]
        extra_roles = [getattr(role, "value", str(role)) for role in self.problem_set if role not in self.role_order]

        if missing_roles or extra_roles:
            detail = []
            if missing_roles:
                detail.append("missing roles: " + ", ".join(missing_roles))
            if extra_roles:
                detail.append("unexpected roles: " + ", ".join(extra_roles))
            raise ValueError("problem_set must contain exactly one entry for each lesson 2 role; " + "; ".join(detail))

        seen_problem_ids = set()
        ordered_problem_set: Dict[ProblemRole, List[Problem]] = {}
        for role in self.role_order:
            problems = self.problem_set[role]
            if len(problems) != 1:
                raise ValueError(f"problem_set[{role.value}] must contain exactly one problem")

            problem = problems[0]
            if problem.recommended_problem_role != role:
                raise ValueError(
                    f"problem_set[{role.value}] must contain a problem tagged with recommended_problem_role={role.value}"
                )
            if problem.problem_id in seen_problem_ids:
                raise ValueError("problem_set must not reuse the same problem across multiple roles")

            seen_problem_ids.add(problem.problem_id)
            ordered_problem_set[role] = [problem]

        self.problem_set = ordered_problem_set
        return self

    def ordered_problem_list(self) -> List[Problem]:
        return [self.problem_set[role][0] for role in self.role_order]
