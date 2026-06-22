import unittest
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch

from adapters.outbound.cache.redis_session_adapter import RedisSessionAdapter
from adapters.outbound.persistence.mongo_session_store import MongoSessionAdapter
from domain.models.overall_models.common import Role
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.message import Message
from domain.models.lesson2_models.meta import SessionMetadata


class _AsyncCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._index]
        self._index += 1
        return doc


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs
        self.find_calls = []
        self.create_index_calls = []
        self.update_one_calls = []

    async def create_index(self, keys, unique=False, name=None):
        self.create_index_calls.append((keys, unique, name))
        return name or "idx"

    async def update_one(self, query, update, upsert=False):
        self.update_one_calls.append((query, update, upsert))

        class _Result:
            upserted_id = "inserted"

        return _Result()

    def find(self, query, sort=None):
        self.find_calls.append((query, sort))
        return _AsyncCursor(self.docs)


class _FakeDb:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return self.collection


class _FakeRedis:
    def __init__(self):
        self.store = {}
        self.set_calls = []

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        self.store[key] = value

    async def scan_iter(self, match=None):
        for key in list(self.store.keys()):
            if match is None:
                yield key
            elif fnmatch(key, match):
                yield key


class SessionStoreOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_mongo_archive_save_is_user_scoped_and_idempotent(self):
        collection = _FakeCollection([])
        adapter = MongoSessionAdapter(db=_FakeDb(collection))

        await adapter.save_messages(
            user_id="user-1",
            session_id="session-1",
            messages=[Message(role=Role.USER, content="hello", correlation_id="corr-1")],
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
            archive_kind="compression",
            archive_request_id="corr-1",
        )

        self.assertEqual(
            collection.create_index_calls,
            [([
                ("user_id", 1),
                ("session_id", 1),
                ("archive_kind", 1),
                ("archive_request_id", 1),
            ], True, "user_id_session_id_archive_kind_archive_request_id_unique")],
        )
        self.assertEqual(
            collection.update_one_calls[0][0],
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "archive_kind": "compression",
                "archive_request_id": "corr-1",
            },
        )
        self.assertTrue(collection.update_one_calls[0][2])

    async def test_mongo_history_query_includes_user_scope(self):
        collection = _FakeCollection(
            [
                {
                    "messages": [
                        {
                            "role": Role.USER.value,
                            "content": "hello",
                            "correlation_id": "corr-1",
                        }
                    ]
                }
            ]
        )
        adapter = MongoSessionAdapter(db=_FakeDb(collection))

        messages = await adapter.get_history_messages("session-1", "user-1")

        self.assertEqual(
            collection.find_calls,
            [({"session_id": "session-1", "user_id": "user-1"}, [("created_at", 1)])],
        )
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, Role.USER)
        self.assertEqual(messages[0].content, "hello")
        self.assertEqual(messages[0].correlation_id, "corr-1")

    async def test_redis_metadata_marks_expired_session_inactive_and_persists_it(self):
        redis = _FakeRedis()
        adapter = RedisSessionAdapter(redis_client=redis, ttl=120, session_timeout=60)
        metadata = SessionMetadata(
            session_id="session-1",
            user_id="user-1",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            is_active=True,
        )
        redis.store["session:session-1:metadata"] = metadata.model_dump_json()

        loaded = await adapter.get_metadata("session-1")

        self.assertIsNotNone(loaded)
        self.assertFalse(loaded.is_active)
        self.assertIsNotNone(loaded.expired_at)
        self.assertEqual(redis.set_calls[0][0], "session:session-1:metadata")
        self.assertEqual(redis.set_calls[0][2], 120)

    async def test_redis_expiration_scan_returns_only_not_yet_closing_sessions(self):
        redis = _FakeRedis()
        adapter = RedisSessionAdapter(redis_client=redis, session_timeout=60)

        expired = SessionMetadata(
            session_id="session-1",
            user_id="user-1",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            is_active=True,
        )
        active = SessionMetadata(
            session_id="session-2",
            user_id="user-2",
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        closing = SessionMetadata(
            session_id="session-3",
            user_id="user-3",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            is_active=False,
            is_closing=True,
        )
        closed = SessionMetadata(
            session_id="session-4",
            user_id="user-4",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
            is_active=False,
            closed_at=datetime.now(timezone.utc),
        )

        redis.store["session:session-1:metadata"] = expired.model_dump_json()
        redis.store["session:session-2:metadata"] = active.model_dump_json()
        redis.store["session:session-3:metadata"] = closing.model_dump_json()
        redis.store["session:session-4:metadata"] = closed.model_dump_json()

        pending = await adapter.list_sessions_pending_expiration_sync()

        self.assertEqual([metadata.session_id for metadata in pending], ["session-1"])
        self.assertFalse(pending[0].is_active)
        self.assertIsNotNone(pending[0].expired_at)


if __name__ == "__main__":
    unittest.main()