import unittest

from fastapi import BackgroundTasks, HTTPException

from adapters.inbound.rest.auth import AuthenticatedUser
from adapters.inbound.rest.lesson2_router import chat, select_exercises, sync_and_close
from adapters.inbound.rest.schemas import ExerciseSelectionRequest, SyncAndCloseRequest
from domain.exceptions import Lesson2ValidationError
from domain.models.lesson2_models.exercise import Approach, ExercisePattern, Lesson2Exercises, Problem
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata
from domain.models.overall_models.common import BloomLevel, ConceptType, Constraint, ProblemRole, Representation
from domain.models.lesson2_models.meta import SessionMetadata
from domain.models.overall_models.response import Lesson2ChatResponse
from domain.models.overall_models.curriculum import Concept, Subject, Topic


class _LearningServiceStub:
    def __init__(self, metadata=None):
        self._session_manager = self
        self.metadata = metadata or SessionMetadata(
            session_id="session-1",
            user_id="user-1",
            is_active=True,
            is_closing=False,
        )
        self.sync_calls = 0
        self.sync_kwargs = []

    async def redis_mark_session_closing(self, session_id: str, user_id: str):
        if self.metadata.user_id != user_id:
            return SessionMetadata(), False
        if self.metadata.closed_at is None and not self.metadata.is_closing:
            self.metadata.is_closing = True
            self.metadata.is_active = False
            return self.metadata, True
        return self.metadata, False

    async def sync_and_close_session(self, **kwargs):
        self.sync_calls += 1
        self.sync_kwargs.append(kwargs)
        return None


class _ChatbotManagerStub:
    def __init__(self, response=None, error=None):
        self.response = response or Lesson2ChatResponse(
            content="Tutor reply",
            usage=[],
            correlation_id="corr-1",
            current_progress=15.0,
        )
        self.error = error
        self.calls = []

    async def run(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class _LessonManagerStub:
    def __init__(self):
        self.calls = []

    async def get_exercise(self, exercise_id: str, user_id: str):
        self.calls.append((exercise_id, user_id))
        return object()


class _ProfileManagerStub:
    def __init__(self):
        self.calls = []

    async def get_student_profile(self, user_id: str):
        self.calls.append(user_id)
        return object()


class _AdaptiveLearningServiceStub:
    async def problem_select(self, student_profile, exercise):
        return Lesson2Exercises(
            problem_set={
                ProblemRole.REINFORCEMENT: [_problem(1, ProblemRole.REINFORCEMENT)],
                ProblemRole.CHALLENGE: [_problem(2, ProblemRole.CHALLENGE)],
                ProblemRole.EXPLORATION: [_problem(3, ProblemRole.EXPLORATION)],
                ProblemRole.EXTENSION: [_problem(4, ProblemRole.EXTENSION)],
            }
        )


def _problem(problem_id: int, role: ProblemRole) -> Problem:
    return Problem(
        problem_id=problem_id,
        question=f"Problem {problem_id}",
        approach_list=[
            Approach(
                summary="Direct approach",
                bloom_level=BloomLevel.APPLY,
                concept_type_used=[ConceptType.METHOD],
                pattern=ExercisePattern(
                    cognitive_operation=[],
                    representation=[Representation.SYMBOLIC],
                    constraints=[Constraint.NONE],
                ),
                approach_answer="42",
                strengths=[],
                weaknesses=[],
                max_attempts=2,
            )
        ],
        final_answer="42",
        open_approach=False,
        recommended_problem_role=role,
        max_approach_trial=1,
    )


def _request() -> SyncAndCloseRequest:
    return SyncAndCloseRequest(
        user_id="user-1",
        session_id="session-1",
        correlation_id="corr-1",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _chat_request(user_id: str = "user-1") -> Lesson2Request:
    return Lesson2Request(
        user_id=user_id,
        session_id="session-1",
        correlation_id="corr-1",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        user_msg="help",
        is_submission=False,
        submission_data=None,
    )


def _selection_request(user_id: str = "user-1") -> ExerciseSelectionRequest:
    return ExerciseSelectionRequest(
        exercise_id="exercise-1",
        user_id=user_id,
        correlation_id="corr-2",
    )


class Lesson2RouterContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_returns_usecase_response_and_forwards_authenticated_user(self):
        chatbot_manager = _ChatbotManagerStub()
        background_tasks = BackgroundTasks()

        response = await chat(
            request=_chat_request(),
            background_tasks=background_tasks,
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            chatbot_manager=chatbot_manager,
        )

        self.assertEqual(response.content, "Tutor reply")
        self.assertEqual(chatbot_manager.calls[0]["user_id"], "user-1")
        self.assertEqual(chatbot_manager.calls[0]["session_id"], "session-1")
        self.assertIs(chatbot_manager.calls[0]["background_task"], background_tasks)

    async def test_chat_maps_validation_error_to_422(self):
        chatbot_manager = _ChatbotManagerStub(error=Lesson2ValidationError("bad submission"))

        with self.assertRaises(HTTPException) as context:
            await chat(
                request=_chat_request(),
                background_tasks=BackgroundTasks(),
                authenticated_user=AuthenticatedUser(user_id="user-1"),
                chatbot_manager=chatbot_manager,
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail, "bad submission")

    async def test_sync_and_close_returns_accepted_payload(self):
        learning_service = _LearningServiceStub()
        background_tasks = BackgroundTasks()
        response = await sync_and_close(
            request=_request(),
            background_tasks=background_tasks,
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            learning_service=learning_service,
        )

        self.assertEqual(response.status, "accepted")
        self.assertEqual(response.correlation_id, "corr-1")
        self.assertEqual(len(background_tasks.tasks), 1)
        self.assertEqual(background_tasks.tasks[0].kwargs["correlation_id"], "corr-1")

    async def test_sync_and_close_is_idempotent_when_already_closing(self):
        metadata = SessionMetadata(
            session_id="session-1",
            user_id="user-1",
            is_active=False,
            is_closing=True,
        )
        learning_service = _LearningServiceStub(metadata=metadata)
        background_tasks = BackgroundTasks()

        response = await sync_and_close(
            request=_request(),
            background_tasks=background_tasks,
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            learning_service=learning_service,
        )

        self.assertEqual(response.status, "closing")
        self.assertEqual(len(background_tasks.tasks), 0)

    async def test_select_exercises_forwards_authenticated_user_to_dependencies(self):
        lesson_manager = _LessonManagerStub()
        profile_manager = _ProfileManagerStub()

        response = await select_exercises(
            request=_selection_request(),
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            lesson_manager=lesson_manager,
            profile_manager=profile_manager,
            adaptive_learning_service=_AdaptiveLearningServiceStub(),
        )

        self.assertEqual([problem.problem_id for problem in response], [1, 2, 3, 4])
        self.assertEqual(profile_manager.calls, ["user-1"])
        self.assertEqual(lesson_manager.calls, [("exercise-1", "user-1")])

    async def test_select_exercises_rejects_authenticated_user_mismatch(self):
        with self.assertRaises(HTTPException) as context:
            await select_exercises(
                request=_selection_request(user_id="user-2"),
                authenticated_user=AuthenticatedUser(user_id="user-1"),
                lesson_manager=_LessonManagerStub(),
                profile_manager=_ProfileManagerStub(),
                adaptive_learning_service=_AdaptiveLearningServiceStub(),
            )

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()