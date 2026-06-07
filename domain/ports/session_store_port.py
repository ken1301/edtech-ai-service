from abc import ABC, abstractmethod

from domain.models.overall_models.message import Message
from domain.models.overall_models.curriculum import Subject
from domain.models.lesson2_models.meta import SessionMetadata

class SessionStorePort(ABC):
    """
    Abstract port for session storage.

    Two concrete adapters implement this port:
        - RedisSessionAdapter   — short-term, in-memory (active session window)
        - MongoSessionAdapter   — long-term, persistent  (history & archival)

    Each adapter only implements the methods that are meaningful for its
    backing store. Calling an inapplicable method raises NotImplementedError.
    """

    # ── Redis operations ──────────────────────────────────────────────────────

    @abstractmethod
    async def get_metadata(self, session_id: str) -> SessionMetadata:
        """
        Return session metadata for the given session.

        Side-effect (Redis adapter only): if `created_at` shows the session has
        exceeded the configured timeout, `is_active` is flipped to False,
        `closed_at` is stamped, and the change is persisted before returning.
        Returns an empty SessionMetadata when the session is not found.
        """

    @abstractmethod
    async def save_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        """Persist the metadata for the given session."""

    @abstractmethod
    async def save_turn(
        self,
        session_id: str,
        user_message: Message,
        assistant_message: Message,
    ) -> None:
        """Append a (user, assistant) message pair to the session history."""

    @abstractmethod
    async def get_right(self, session_id: str, limit: int) -> list[Message]:
        """Return the *N* most recent messages (newest end of the list)."""

    @abstractmethod
    async def get_left(self, session_id: str, limit: int) -> list[Message]:
        """Return the *N* oldest messages (oldest end of the list)."""

    @abstractmethod
    async def delete_left(self, session_id: str, limit: int) -> None:
        """Remove the *N* oldest messages from the session history."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete all data associated with the given session."""

    # ── MongoDB operations ────────────────────────────────────────────────────

    @abstractmethod
    async def save_messages(
        self,
        user_id: str,
        session_id: str,
        messages: list[Message],
        subject: Subject,
        topic: str,
    ) -> None:
        """
        Persist a batch of messages for long-term storage.
        Called once per history-compression cycle and once on session close.
        """

    @abstractmethod
    async def get_history_messages(self, session_id: str) -> list[Message]:
        """
        Return the full message history for a session, ordered by insertion time.
        May merge multiple batched documents into a single flat list.
        """