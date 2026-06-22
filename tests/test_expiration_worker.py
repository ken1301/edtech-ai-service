import unittest
from datetime import datetime, timedelta, timezone

from application.stateless_services.learning_service import LearningService
from domain.models.lesson2_models.meta import SessionMetadata
from domain.models.overall_models.curriculum import Concept, Subject, Topic


class _SessionManagerStub:
    def __init__(self, expired_sessions=None, newly_marked=True):
        self.expired_sessions = expired_sessions or []
        self.newly_marked = newly_marked
        self.mark_calls = []

    async def redis_list_sessions_pending_expiration_sync(self):
        return list(self.expired_sessions)

    async def redis_mark_session_closing(self, session_id: str, user_id: str):
        self.mark_calls.append((session_id, user_id))
        metadata = next(item for item in self.expired_sessions if item.session_id == session_id)
        metadata.is_closing = True
        metadata.is_active = False
        return metadata, self.newly_marked


class _LearningServiceHarness(LearningService):
    def __init__(self, session_manager):
        self._session_manager = session_manager
        self.sync_calls = []

    async def sync_and_close_session(self, **kwargs):
        self.sync_calls.append(kwargs)


def _expired_metadata() -> SessionMetadata:
    return SessionMetadata(
        session_id="session-1",
        user_id="user-1",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        expired_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        is_active=False,
    )


class ExpirationWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_expired_sessions_marks_and_processes_expired_sessions(self):
        metadata = _expired_metadata()
        session_manager = _SessionManagerStub(expired_sessions=[metadata])
        learning_service = _LearningServiceHarness(session_manager=session_manager)

        processed = await learning_service.sync_expired_sessions()

        self.assertEqual(processed, 1)
        self.assertEqual(session_manager.mark_calls, [("session-1", "user-1")])
        self.assertEqual(len(learning_service.sync_calls), 1)
        self.assertTrue(learning_service.sync_calls[0]["correlation_id"].startswith("expiry:session-1:"))

    async def test_sync_expired_sessions_skips_already_marked_sessions(self):
        metadata = _expired_metadata()
        session_manager = _SessionManagerStub(expired_sessions=[metadata], newly_marked=False)
        learning_service = _LearningServiceHarness(session_manager=session_manager)

        processed = await learning_service.sync_expired_sessions()

        self.assertEqual(processed, 0)
        self.assertEqual(len(learning_service.sync_calls), 0)


if __name__ == "__main__":
    unittest.main()