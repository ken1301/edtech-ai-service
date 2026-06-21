from pydantic import BaseModel
from typing import Dict, List

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.token_usage import TokenUsage

class MultipleChoiceQuestion(BaseModel):
    question: str
    options: Dict[str, str]  # e.g., {"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"}
    answer: str

class FillInTheBlankQuestion(BaseModel):
    question: str  # e.g., "The capital of France is _____."
    answer: str  # e.g., "Paris"

class TrueFalseQuestion(BaseModel):
    question: str  # e.g., "The Earth is flat."
    answer: bool  # True or False

class Lesson1Exercises(BaseModel):
    multiple_choice_questions: List[MultipleChoiceQuestion]
    fill_in_the_blank_questions: List[FillInTheBlankQuestion] 
    # true_false_questions: List[TrueFalseQuestion]  

class Lesson1KnowledgeContent(BaseModel):
    pass

class Lesson1CreationOutput(BaseModel):
    user_id: str

    content: Lesson1KnowledgeContent
    exercises: Lesson1Exercises

    summary: str  # A concise summary of the lesson content

class Lesson1CreationResponse(BaseModel):
    output: Lesson1CreationOutput
    usage: TokenUsage
    correlation_id: str

class CreateLessonMetadata(BaseModel):
    lesson_id: str
    summary: str
