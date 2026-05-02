from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from domain.ports.db_port import MongoPort
from domain.models.profile import StudentProfile


class MongoAdapter(MongoPort):
    """MongoDB adapter for student profile management"""
    
    def __init__(self, url: str, db_name: str):
        """Initialize MongoDB adapter
        
        Args:
            url: MongoDB connection URL
            db_name: Database name
        """
        self._client = AsyncIOMotorClient(url)
        self._db = self._client[db_name]
        self._collection = self._db["student_profiles"]

    async def get_student_profile(self, student_id: str) -> Optional[StudentProfile]:
        """Retrieve student profile
        
        Args:
            student_id: Unique student identifier
            
        Returns:
            StudentProfile if found, None otherwise
        """
        doc = await self._collection.find_one({"_id": student_id})
        if not doc:
            return None
        return StudentProfile(**doc)

    async def update_student_preferences(self, student_id: str, data: dict) -> bool:
        """Update student preferences
        
        Args:
            student_id: Student identifier
            data: New preferences data
            
        Returns:
            True if update was successful
        """
        result = await self._collection.update_one(
            {"_id": student_id},
            {"$set": {"preferences": data}}
        )
        return result.modified_count > 0

    async def update_knowledge_map(self, student_id: str, subject: str, topic: str, data: dict) -> bool:
        """Update knowledge map for a specific topic
        
        Uses MongoDB dot notation to update nested objects without losing other data.
        
        Args:
            student_id: Student identifier
            subject: Subject (e.g., 'math')
            topic: Topic within subject (e.g., 'derivative')
            data: Topic mastery data
            
        Returns:
            True if update was successful
        """
        update_path = f"knowledge_map.{subject}.{topic}"
        result = await self._collection.update_one(
            {"_id": student_id},
            {"$set": {update_path: data}},
        )
        return result.modified_count > 0

    async def save_profile(self, profile: StudentProfile) -> bool:
        """Save or replace entire student profile
        
        Args:
            profile: StudentProfile to save
            
        Returns:
            True if operation was acknowledged
        """
        data = profile.model_dump(by_alias=True)
        result = await self._collection.replace_one(
            {"_id": data["_id"]},
            data,
            upsert=True,
        )
        return result.acknowledged

    def close(self):
        """Close MongoDB connection on app shutdown"""
        self._client.close()

