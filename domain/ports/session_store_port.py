from abc import ABC, abstractmethod
from typing import Any, Dict, List

from domain.models.message import Message


class SessionStorePort(ABC):
    @abstractmethod
    async def get_history(self, session_id: str) -> List[Message]:
        pass

    @abstractmethod
    async def save_message(self, session_id: str, message: Message) -> bool:
        pass

    @abstractmethod
    async def get_metadata(self, session_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def save_metadata(self, session_id: str, metadata: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        pass
