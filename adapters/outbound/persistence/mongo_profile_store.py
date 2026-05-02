from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from domain.ports.profile_store_port import ProfileStorePort
from domain.models.profile import StudentProfile


class MongoProfileStore(ProfileStorePort):
    """MongoDB adapter for student profile persistence."""

    def __init__(self, url: str, db_name: str):
        self._client = AsyncIOMotorClient(url)
        self._db = self._client[db_name]
        self._collection = self._db["student_profiles"]

    async def get_student_profile(self, student_id: str) -> Optional[StudentProfile]:
        doc = await self._collection.find_one({"_id": student_id})
        if not doc:
            return None
        return StudentProfile(**doc)

    async def update_student_preferences(self, student_id: str, data: dict) -> bool:
        result = await self._collection.update_one(
            {"_id": student_id},
            {"$set": {"preferences": data}},
        )
        return result.modified_count > 0

    async def update_knowledge_map(self, student_id: str, subject: str, topic: str, data: dict) -> bool:
        update_path = f"knowledge_map.{subject}.{topic}"
        result = await self._collection.update_one(
            {"_id": student_id},
            {"$set": {update_path: data}},
        )
        return result.modified_count > 0

    async def save_profile(self, profile: StudentProfile) -> bool:
        data = profile.model_dump(by_alias=True)
        result = await self._collection.replace_one(
            {"_id": data["_id"]},
            data,
            upsert=True,
        )
        return result.acknowledged

    def close(self):
        self._client.close()
