import unittest
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks

from application.use_cases.chatbot_usecase import ChatbotUseCase
from domain.exceptions import (
    AuthorizationError,
    Lesson2SessionConflictError,
    Lesson2ValidationError,
    SessionClosedError,
    SessionNotFoundError,
)
from domain.models.overall_models.common import Role
from domain.models.overall_models.message import Message
from domain.models.overall_models.response import Lesson2ChatResponse
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata
from domain.models.overall_models.curriculum import Concept, Subject, Topic


def _request() -> Lesson2Request:
    return Lesson2Request(
        user_id="user-1",
        session_id="session-1",
        correlation_id="corr-1",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        user_msg="help",
        is_submission=False,
        submission_data=None,
    )


class _SessionManagerStub:
    def __init__(self, metadata, messages=None):
        self.metadata = metadata
        self.messages = messages or []
        self.delete_left_calls = []
        self.save_turn_with_metadata_calls = []
        self.prepare_calls = []
        self.abandon_calls = []
        self.guard_calls = []

    @asynccontextmanager
    async def session_guard(self, session_id: str):
        self.guard_calls.append(session_id)
        yield

    async def prepare_lesson2_chat_request(self, session_id: str, user_id: str, correlation_id: str):
        self.prepare_calls.append((session_id, user_id, correlation_id))
        if self.metadata is None:
            return None, None

        last_completed_correlation_id = getattr(self.metadata, "last_completed_correlation_id", None)
        last_response_content = getattr(self.metadata, "last_response_content", None)
        last_response_usage = getattr(self.metadata, "last_response_usage", [])
        last_response_progress = getattr(self.metadata, "last_response_progress", None)
        active_correlation_id = getattr(self.metadata, "active_correlation_id", None)

        if (
            last_completed_correlation_id == correlation_id
            and last_response_content is not None
            and last_response_progress is not None
        ):
            return self.metadata, Lesson2ChatResponse(
                content=last_response_content,
                usage=list(last_response_usage),
                current_progress=last_response_progress,
            )
        if active_correlation_id == correlation_id:
            raise Lesson2SessionConflictError("A request with this correlation_id is already in progress.")
        if active_correlation_id is not None:
            raise Lesson2SessionConflictError("Another request is already in progress for this session.")
        self.metadata.active_correlation_id = correlation_id
        return self.metadata, None

    async def abandon_lesson2_chat_request(self, session_id: str, metadata: SessionMetadata, correlation_id: str):
        self.abandon_calls.append((session_id, correlation_id))
        if getattr(metadata, "active_correlation_id", None) == correlation_id:
            metadata.active_correlation_id = None

    async def redis_get_all_messages(self, session_id: str):
        return list(self.messages)

    async def redis_get_metadata(self, session_id: str):
        return self.metadata

    async def redis_save_metadata(self, session_id: str, metadata: SessionMetadata):
        self.metadata = metadata

    async def redis_save_turn(self, session_id: str, user_message, assistant_message):
        self.messages.extend([user_message, assistant_message])

    async def redis_save_turn_with_metadata(self, session_id: str, user_message, assistant_message, metadata: SessionMetadata):
        self.messages.extend([user_message, assistant_message])
        self.metadata = metadata
        self.save_turn_with_metadata_calls.append((session_id, metadata.turn_count))

    async def redis_delete_left(self, session_id: str, limit: int):
        self.delete_left_calls.append((session_id, limit))
        self.messages = self.messages[limit:]


class _LearningServiceStub:
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.compress_calls = []

    async def compress_session_history(self, **kwargs):
        self.compress_calls.append(kwargs)
        metadata = kwargs["metadata"]
        metadata.turn_count -= kwargs["TURN_TO_COMPRESS"]
        if self.session_manager is not None:
            await self.session_manager.redis_delete_left(kwargs["session_id"], kwargs["MSG_TO_COMPRESS"])
        return metadata

    async def sync_and_close_session(self, **kwargs):
        return None


class _OrchestrationValidationStub:
    async def process(self, **kwargs):
        raise Lesson2ValidationError("bad submission")


class _OrchestrationSuccessStub:
    def __init__(self):
        self.calls = []

    async def process(self, **kwargs):
        self.calls.append(kwargs)
        metadata = kwargs["session_metadata"]
        return "response", metadata, [], None


class ChatbotUseCaseContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_session_raises_not_found(self):
        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(None),
            learning_service=_LearningServiceStub(),
            orchestration=_OrchestrationValidationStub(),
        )

        with self.assertRaises(SessionNotFoundError):
            await usecase.run(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                request=_request(),
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                background_task=BackgroundTasks(),
            )

    async def test_closed_session_raises_conflict(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-1", is_active=False)
        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(metadata),
            learning_service=_LearningServiceStub(),
            orchestration=_OrchestrationValidationStub(),
        )

        with self.assertRaises(SessionClosedError):
            await usecase.run(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                request=_request(),
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                background_task=BackgroundTasks(),
            )

    async def test_expired_session_raises_conflict(self):
        metadata = SessionMetadata(
            session_id="session-1",
            user_id="user-1",
            is_active=False,
            expired_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(metadata),
            learning_service=_LearningServiceStub(),
            orchestration=_OrchestrationValidationStub(),
        )

        with self.assertRaises(SessionClosedError):
            await usecase.run(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                request=_request(),
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                background_task=BackgroundTasks(),
            )

    async def test_wrong_user_still_raises_authorization(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-2", is_active=True)
        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(metadata),
            learning_service=_LearningServiceStub(),
            orchestration=_OrchestrationValidationStub(),
        )

        with self.assertRaises(AuthorizationError):
            await usecase.run(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                request=_request(),
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                background_task=BackgroundTasks(),
            )

    async def test_lesson2_validation_error_is_preserved(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-1", is_active=True)
        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(metadata),
            learning_service=_LearningServiceStub(),
            orchestration=_OrchestrationValidationStub(),
        )

        with self.assertRaises(Lesson2ValidationError):
            await usecase.run(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                request=_request(),
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                background_task=BackgroundTasks(),
            )

    async def test_successful_turn_increments_turn_count_with_turn_persistence(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-1", is_active=True, turn_count=1)
        session_manager = _SessionManagerStub(metadata)
        orchestration = _OrchestrationSuccessStub()
        usecase = ChatbotUseCase(
            session_manager=session_manager,
            learning_service=_LearningServiceStub(),
            orchestration=orchestration,
        )

        response = await usecase.run(
            user_id="user-1",
            session_id="session-1",
            correlation_id="corr-1",
            request=_request(),
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
            background_task=BackgroundTasks(),
        )

        self.assertIsInstance(response, Lesson2ChatResponse)
        self.assertEqual(response.content, "response")
        self.assertEqual(response.current_progress, 0.0)
        self.assertEqual(session_manager.guard_calls, ["session-1"])
        self.assertEqual(session_manager.metadata.turn_count, 2)
        self.assertEqual(session_manager.save_turn_with_metadata_calls, [("session-1", 2)])
        self.assertEqual(len(orchestration.calls), 1)
        self.assertEqual(orchestration.calls[0]["history_msg"][-1].content, "help")
        self.assertFalse(orchestration.calls[0]["history_msg"][-1].is_submission)

    async def test_successful_turn_propagates_current_progress(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-1", is_active=True, turn_count=1)

        class _ProgressOrchestrationStub:
            async def process(self, **kwargs):
                updated_metadata = kwargs["session_metadata"]
                updated_metadata.current_progress = 37.5
                return "response", updated_metadata, [{"tokens": 3}], None

        usecase = ChatbotUseCase(
            session_manager=_SessionManagerStub(metadata),
            learning_service=_LearningServiceStub(),
            orchestration=_ProgressOrchestrationStub(),
        )

        response = await usecase.run(
            user_id="user-1",
            session_id="session-1",
            correlation_id="corr-1",
            request=_request(),
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
            background_task=BackgroundTasks(),
        )

        self.assertEqual(response.current_progress, 37.5)
        self.assertEqual(response.usage, [{"tokens": 3}])

    async def test_compression_trims_messages_once(self):
        metadata = SessionMetadata(session_id="session-1", user_id="user-1", is_active=True, turn_count=21)
        messages = [
            Message(
                role=Role.USER if index % 2 == 0 else Role.ASSISTANT,
                content=f"message-{index}",
            )
            for index in range(24)
        ]
        session_manager = _SessionManagerStub(metadata, messages=messages)
        learning_service = _LearningServiceStub(session_manager=session_manager)
        usecase = ChatbotUseCase(
            session_manager=session_manager,
            learning_service=learning_service,
            orchestration=_OrchestrationSuccessStub(),
        )

        await usecase.run(
            user_id="user-1",
            session_id="session-1",
            correlation_id="corr-1",
            request=_request(),
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
            background_task=BackgroundTasks(),
        )

        self.assertEqual(session_manager.delete_left_calls, [("session-1", 20)])
        self.assertEqual(session_manager.metadata.turn_count, 12)
        self.assertEqual(learning_service.compress_calls[0]["correlation_id"], "corr-1")


if __name__ == "__main__":
    unittest.main()