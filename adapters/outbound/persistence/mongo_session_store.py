from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any, Dict, List

from domain.ports.session_store_port import SessionStorePort
from domain.models.message import Message


class MongoSessionStore(SessionStorePort):
    """MongoDB adapter for long-term session/conversation persistence.

    Use this when you need durable session storage (e.g. for audit or replay).
    For hot-path in-flight sessions, prefer RedisAdapter.
    """

    def __init__(self, url: str, db_name: str):
        self._client = AsyncIOMotorClient(url)
        self._db = self._client[db_name]
        self._messages = self._db["session_messages"]
        self._metadata = self._db["session_metadata"]

    async def get_history(self, session_id: str) -> List[Message]:
        cursor = self._messages.find(
            {"session_id": session_id},
            sort=[("created_at", 1)],
        )
        docs = await cursor.to_list(length=None)
        return [Message(**doc) for doc in docs]

    async def save_message(self, session_id: str, message: Message) -> bool:
        data = message.model_dump()
        data["session_id"] = session_id
        await self._messages.insert_one(data)
        return True

    async def get_metadata(self, session_id: str) -> Dict[str, Any]:
        doc = await self._metadata.find_one({"_id": session_id})
        if not doc:
            return {}
        doc.pop("_id", None)
        return doc

    async def save_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        result = await self._metadata.replace_one(
            {"_id": session_id},
            {"_id": session_id, **metadata},
            upsert=True,
        )
        return result.acknowledged

    async def clear_session(self, session_id: str) -> None:
        await self._messages.delete_many({"session_id": session_id})
        await self._metadata.delete_one({"_id": session_id})

    def close(self):
        self._client.close()
