import json
from typing import Any, Dict, List

import redis.asyncio as redis

from domain.ports.cache_port import CachePort
from domain.models.message import Message


class RedisAdapter(CachePort):
    """Redis adapter — implements SessionStorePort (hot session) + CachePort (generic KV)."""

    MAX_HISTORY_SIZE = 50  # keep up to 50 raw messages (before compression kicks in)
    SESSION_TTL_SECONDS = 60 * 60 * 2  # 2 h — must exceed SessionManager.SESSION_TIMEOUT_SECONDS

    def __init__(self, url: str):
        self._client = redis.from_url(url, decode_responses=True)

    # ------------------------------------------------------------------
    # SessionStorePort
    # ------------------------------------------------------------------

    async def get_history(self, session_id: str) -> List[Message]:
        data = await self._client.lrange(f"session:{session_id}", 0, -1)
        return [Message(**json.loads(msg)) for msg in data]

    async def save_message(self, session_id: str, message: Message) -> bool:
        key = f"session:{session_id}"
        await self._client.rpush(key, message.model_dump_json())
        await self._client.ltrim(key, -self.MAX_HISTORY_SIZE, -1)
        await self._client.expire(key, self.SESSION_TTL_SECONDS)
        return True

    async def get_metadata(self, session_id: str) -> Dict[str, Any]:
        data = await self._client.get(f"session:{session_id}:metadata")
        return json.loads(data) if data else {}

    async def save_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        await self._client.set(
            f"session:{session_id}:metadata",
            json.dumps(metadata, ensure_ascii=False),
            ex=self.SESSION_TTL_SECONDS,
        )
        return True

    async def clear_session(self, session_id: str) -> None:
        await self._client.delete(
            f"session:{session_id}",
            f"session:{session_id}:metadata",
        )

    # ------------------------------------------------------------------
    # CachePort (generic KV)
    # ------------------------------------------------------------------

    async def get_cache(self, key: str) -> Any:
        data = await self._client.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            return data

    async def set_cache(self, key: str, value: Any, ttl: int = 3600) -> bool:
        serialized = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        await self._client.set(key, serialized, ex=ttl)
        return True

    async def delete_cache(self, key: str) -> None:
        await self._client.delete(key)

    async def close(self):
        await self._client.aclose()
