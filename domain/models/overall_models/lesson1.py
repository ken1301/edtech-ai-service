from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from domain.models.lesson2_models.exercise import Exercise as Lesson2Exercise
from domain.models.overall_models.token_usage import TokenUsage
from domain.models.overall_models.common import ConceptType, BloomLevel
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.evaluate import Phase

# ── Enums ─────────────────────────────────────────────────────────────────────

class HookType(str, Enum):
    """Which P-D-E-O 'Problem' entry point was chosen for this lesson."""
    real_world    = "real_world"     # new real-life scenario, no prior lesson dependency
    knowledge_gap = "knowledge_gap"  # previous concept hits a hard wall
    optimization  = "optimization"   # previous concept works but is clunky; this is the upgrade


class ExerciseType(str, Enum):
    MULTIPLE_CHOICE    = "multiple_choice"
    FILL_IN_THE_BLANK  = "fill_in_the_blank"
    TRUE_FALSE         = "true_false"
    SHORT_ANSWER       = "short_answer"

# ── Knowledge ─────────────────────────────────────────────────────────────────

class KnowledgeItem(BaseModel):
    content_type: ConceptType  # one of: definition, formula, method, property,
                               #         application, common_mistake, visualization
    title: str
    content: str               # markdown string — headers, bold, code blocks, blockquotes, etc.
    is_core: bool              # True  → required to solve Lesson 2 Problem 1
    from_source: bool          # False → AI-supplied gap; needs content-team review


class Lesson1Knowledge(BaseModel):
    concept_name: str
    hook_type: HookType
    hook: str                  # markdown string — the P-D-E-O "Problem" entry point
    items: List[KnowledgeItem]
    prerequisites: List[str]   # prior knowledge assumed, not taught here


# ── Exercises ─────────────────────────────────────────────────────────────────

class Lesson1Exercise(BaseModel):
    """
    Unified exercise model — replaces the old split MultipleChoice / FillInTheBlank / TrueFalse.

    answer encoding by exercise_type:
      multiple_choice   → the option text (not index)
      fill_in_the_blank → the missing token(s)
      true_false        → "true" or "false"
      short_answer      → the expected answer string
    """
    exercise_type: ExerciseType
    question: str
    options: List[str] = Field(default_factory=list)  # non-empty only for multiple_choice
    answer: str
    explanation: str
    concept_type_used: List[ConceptType]
    bloom_level: BloomLevel
    pdeo_phase: Phase
    targets_problem_1: bool  # True → direct evidence the student can attempt L2 Problem 1


Exercise = Lesson1Exercise


# ── Summary ───────────────────────────────────────────────────────────────────

class Lesson1Summary(BaseModel):
    text: str                    # 3–6 sentences briefing the Lesson 2 chatbot
    core_skills: List[str]       # concrete, actionable skills the student can now perform
    ready_for_problem_1: bool    # judgment: is the foundation sufficient for L2 P1?


# ── Root output ───────────────────────────────────────────────────────────────

class Lesson1CreationOutput(BaseModel):
    user_id: str
    knowledge: Lesson1Knowledge  
    exercises: List[Lesson1Exercise]   
    summary: Lesson1Summary      


class Lesson1StoredSection(BaseModel):
    learning_content: Lesson1Knowledge
    exercise: List[Lesson1Exercise]
    summary: Lesson1Summary


class Lesson2StoredSection(BaseModel):
    exercise: Lesson2Exercise
    summary: str


class LessonArtifact(BaseModel):
    root_lesson_id: Optional[str] = None
    user_id: str
    lesson1: Optional[Lesson1StoredSection] = None
    lesson2: Optional[Lesson2StoredSection] = None
    subject: Subject
    topic: Topic
    concept: Concept


class Lesson1StoredArtifact(LessonArtifact):
    lesson1: Lesson1StoredSection


class Lesson2StoredArtifact(LessonArtifact):
    lesson1: Lesson1StoredSection
    lesson2: Lesson2StoredSection
    

class CreateLessonMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str
    lesson_id: str
    lesson1_exercise_id: str
    lesson2_exercise_id: Optional[str] = None
    lesson1_summary: Lesson1Summary = Field(alias="summary")
    lesson2_summary: Optional[str] = None
    subject: Subject
    topic: Topic
    concept: Concept

    @property
    def summary(self) -> Lesson1Summary:
        return self.lesson1_summary