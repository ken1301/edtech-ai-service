import time

from infrastructure.logging import logger

from domain.ports.cache_port import CachePort

class SessionManager:
    """
    Manages chat sessions, including creation, retrieval, and deletion of session data. Handles session state and history management.
    """

    SESSION_TIMEOUT_SECONDS = 3600  # 1 hour

    def __init__(self, cache_gateway: CachePort):
        self.cache = cache_gateway

    async def get_or_create_session(self, session_id: str):
        """
        Retrieve existing session metadata or create a new session if it doesn't exist or has expired.
        """

        meta = await self.cache.get_metadata(session_id)
        if not meta:
            # Tạo mới hoàn toàn
            meta = {"start_time": time.time(), "is_active": True}
            await self.cache.save_metadata(session_id, meta)
            logger.info("SESSION_CREATED", session_id=session_id)
            return meta, True # True là session mới

        # Kiểm tra 60p
        if time.time() - meta["start_time"] > self.SESSION_TIMEOUT_SECONDS:
            meta["is_active"] = False
            await self.cache.save_metadata(session_id, meta)
            logger.error("SESSION_EXPIRED", session_id=session_id)
            return meta, False # Session đã hết hạn
        
        logger.info("SESSION_RETRIEVED", session_id=session_id)
        return meta, True # Còn hạn
    
    async def save_metadata(self, session_id: str, metadata: dict) -> bool:
        """Lưu metadata của session (ví dụ: subject, topic, system_prompt)"""

    
        return await self.cache.save_metadata(session_id, metadata)