import unittest
from contextlib import asynccontextmanager

from application.services.session_manager import SessionManager


class _RedisStoreWithoutDistributedLock:
    pass


class _RedisStoreWithDistributedLock:
    def __init__(self):
        self.calls = []

    @asynccontextmanager
    async def build_session_lock(self, session_id: str, timeout_seconds: int):
        self.calls.append((session_id, timeout_seconds, "enter"))
        try:
            yield
        finally:
            self.calls.append((session_id, timeout_seconds, "exit"))


class _MongoStoreStub:
    pass


class SessionManagerLockingTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_guard_prefers_redis_backed_lock_when_available(self):
        redis_store = _RedisStoreWithDistributedLock()
        manager = SessionManager(redis_session_store=redis_store, mongo_session_store=_MongoStoreStub())

        async with manager.session_guard("session-1"):
            pass

        self.assertEqual(
            redis_store.calls,
            [
                ("session-1", 30, "enter"),
                ("session-1", 30, "exit"),
            ],
        )

    async def test_session_guard_falls_back_to_local_lock_when_redis_lock_unavailable(self):
        manager = SessionManager(
            redis_session_store=_RedisStoreWithoutDistributedLock(),
            mongo_session_store=_MongoStoreStub(),
        )

        async with manager.session_guard("session-1"):
            self.assertIn("session-1", manager._session_locks)


if __name__ == "__main__":
    unittest.main()