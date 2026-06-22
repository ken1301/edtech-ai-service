import unittest

from fastapi import HTTPException

from adapters.inbound.rest.auth import AuthenticatedUser
from adapters.inbound.rest.create_lesson_router import extract_document, extract_exercises
from adapters.inbound.rest.schemas import DocumentExtractionRequest, ExerciseExtractionRequest
from domain.exceptions import CreateLessonUseCaseError
from domain.models.lesson2_models.common import Phase
from domain.models.lesson2_models.exercise import Approach, Exercise as Lesson2Exercise, ExercisePattern, Problem
from domain.models.overall_models.common import (
    ApproachStrength,
    ApproachWeakness,
    BloomLevel,
    CognitiveOperation,
    ConceptType,
    Constraint,
    ProblemRole,
    Representation,
)
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.lesson1 import (
    Exercise,
    ExerciseType,
    HookType,
    KnowledgeItem,
    Lesson1CreationOutput,
    Lesson1Knowledge,
    Lesson1Summary,
)
from domain.models.overall_models.response import Lesson1CreationResponse, Lesson2ExerciseExtractionResponse
from domain.models.overall_models.token_usage import TokenUsage


def _document_request() -> DocumentExtractionRequest:
    return DocumentExtractionRequest(
        user_id="user-1",
        correlation_id="corr-1",
        lesson_id="lesson-1",
        document_url="https://example.com/lesson.pdf",
        previous_lesson=[],
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _exercise_request() -> ExerciseExtractionRequest:
    return ExerciseExtractionRequest(
        user_id="user-1",
        correlation_id="corr-2",
        lesson_id="lesson-1",
        document_url="https://example.com/lesson.pdf",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _lesson1_response() -> Lesson1CreationResponse:
    return Lesson1CreationResponse(
        output=Lesson1CreationOutput(
            user_id="user-1",
            knowledge=Lesson1Knowledge(
                concept_name="functions",
                hook_type=HookType.real_world,
                hook="Hook",
                items=[
                    KnowledgeItem(
                        content_type=ConceptType.DEFINITION,
                        title="Definition",
                        content="A function groups reusable logic.",
                        is_core=True,
                        from_source=True,
                    )
                ],
                prerequisites=["variables"],
            ),
            exercises=[
                Exercise(
                    exercise_type=ExerciseType.SHORT_ANSWER,
                    question="What is a function?",
                    answer="Reusable logic",
                    explanation="Functions package behavior.",
                    concept_type_used=[ConceptType.DEFINITION],
                    bloom_level=BloomLevel.REMEMBER,
                    pdeo_phase=Phase.PROBLEM,
                    targets_problem_1=True,
                )
            ],
            summary=Lesson1Summary(
                text="Student can explain what functions are.",
                core_skills=["identify functions"],
                ready_for_problem_1=True,
            ),
        ),
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        correlation_id="corr-1",
    )


def _lesson2_response() -> Lesson2ExerciseExtractionResponse:
    roles = [
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
    ]
    problem_list = []
    for index, role in enumerate(roles, start=1):
        problem_list.append(
            Problem(
                problem_id=index,
                question=f"Question {index}",
                attachment_url=[],
                approach_list=[
                    Approach(
                        summary=f"Approach {index}",
                        bloom_level=BloomLevel.APPLY,
                        concept_type_used=[ConceptType.METHOD],
                        pattern=ExercisePattern(
                            cognitive_operation=[CognitiveOperation.APPLY],
                            representation=[Representation.VERBAL],
                            constraints=[Constraint.NONE],
                        ),
                        approach_answer=f"Answer {index}",
                        strengths=[ApproachStrength.EASY_TO_IMPLEMENT],
                        weaknesses=[ApproachWeakness.CASE_SPECIFIC],
                        max_attempts=3,
                    )
                ],
                final_answer=f"Final {index}",
                open_approach=False,
                recommended_problem_role=role,
                max_approach_trial=2,
            )
        )

    return Lesson2ExerciseExtractionResponse(
        exercise_id="lesson-1",
        output=Lesson2Exercise(
            problem_list=problem_list,
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
            user_id="user-1",
        ),
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        correlation_id="corr-2",
    )


class _CreateLessonManagerStub:
    def __init__(self, lesson1_response=None, lesson2_response=None, lesson1_error=None, lesson2_error=None):
        self.lesson1_response = lesson1_response
        self.lesson2_response = lesson2_response
        self.lesson1_error = lesson1_error
        self.lesson2_error = lesson2_error
        self.lesson1_calls = []
        self.lesson2_calls = []

    async def lesson1_run(self, **kwargs):
        self.lesson1_calls.append(kwargs)
        if self.lesson1_error is not None:
            raise self.lesson1_error
        return self.lesson1_response

    async def lesson2_run(self, **kwargs):
        self.lesson2_calls.append(kwargs)
        if self.lesson2_error is not None:
            raise self.lesson2_error
        return self.lesson2_response


class CreateLessonRouterContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_document_rejects_authenticated_user_mismatch(self):
        manager = _CreateLessonManagerStub(lesson1_response=_lesson1_response())

        with self.assertRaises(HTTPException) as context:
            await extract_document(
                request=_document_request(),
                authenticated_user=AuthenticatedUser(user_id="user-2"),
                lesson_creation_manager=manager,
            )

        self.assertEqual(context.exception.status_code, 403)

    async def test_extract_document_returns_usecase_response_and_forwards_authenticated_user(self):
        manager = _CreateLessonManagerStub(lesson1_response=_lesson1_response())

        response = await extract_document(
            request=_document_request(),
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            lesson_creation_manager=manager,
        )

        self.assertIsInstance(response, Lesson1CreationResponse)
        self.assertEqual(response.correlation_id, "corr-1")
        self.assertEqual(manager.lesson1_calls[0]["user_id"], "user-1")
        self.assertEqual(manager.lesson1_calls[0]["lesson_id"], "lesson-1")

    async def test_extract_document_preserves_usecase_error_detail(self):
        manager = _CreateLessonManagerStub(
            lesson1_error=CreateLessonUseCaseError("Failed to transform document to Markdown format.")
        )

        with self.assertRaises(HTTPException) as context:
            await extract_document(
                request=_document_request(),
                authenticated_user=AuthenticatedUser(user_id="user-1"),
                lesson_creation_manager=manager,
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail, "Failed to transform document to Markdown format.")

    async def test_extract_exercises_returns_usecase_response_and_forwards_authenticated_user(self):
        manager = _CreateLessonManagerStub(lesson2_response=_lesson2_response())

        response = await extract_exercises(
            request=_exercise_request(),
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            lesson_creation_manager=manager,
        )

        self.assertIsInstance(response, Lesson2ExerciseExtractionResponse)
        self.assertEqual(response.exercise_id, "lesson-1")
        self.assertEqual(response.correlation_id, "corr-2")
        self.assertEqual(manager.lesson2_calls[0]["user_id"], "user-1")
        self.assertEqual(manager.lesson2_calls[0]["lesson_id"], "lesson-1")

    async def test_extract_exercises_rejects_authenticated_user_mismatch(self):
        manager = _CreateLessonManagerStub(lesson2_response=_lesson2_response())

        with self.assertRaises(HTTPException) as context:
            await extract_exercises(
                request=_exercise_request(),
                authenticated_user=AuthenticatedUser(user_id="user-2"),
                lesson_creation_manager=manager,
            )

        self.assertEqual(context.exception.status_code, 403)

    async def test_extract_exercises_preserves_usecase_error_detail(self):
        manager = _CreateLessonManagerStub(
            lesson2_error=CreateLessonUseCaseError("Failed to fetch document from cloud storage.")
        )

        with self.assertRaises(HTTPException) as context:
            await extract_exercises(
                request=_exercise_request(),
                authenticated_user=AuthenticatedUser(user_id="user-1"),
                lesson_creation_manager=manager,
            )

        self.assertEqual(context.exception.status_code, 500)
        self.assertEqual(context.exception.detail, "Failed to fetch document from cloud storage.")


if __name__ == "__main__":
    unittest.main()