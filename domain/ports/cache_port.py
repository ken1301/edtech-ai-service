from abc import abstractmethod
from typing import Any, Dict

from domain.ports.session_store_port import SessionStorePort


class CachePort(SessionStorePort):
    """Extended session store with generic key-value cache operations."""

    @abstractmethod
    async def get_cache(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set_cache(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass

    @abstractmethod
    async def delete_cache(self, key: str) -> None:
        pass
