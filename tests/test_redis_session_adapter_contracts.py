import unittest

from adapters.outbound.cache.redis_session_adapter import RedisSessionAdapter
from domain.models.lesson2_models.meta import SessionMetadata


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.set_calls = []

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value
        self.set_calls.append((key, value, ex))


class RedisSessionAdapterContractsTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_metadata_returns_none_for_missing_session(self):
        adapter = RedisSessionAdapter(redis_client=_FakeRedis())

        metadata = await adapter.get_metadata("missing-session")

        self.assertIsNone(metadata)


if __name__ == "__main__":
    unittest.main()