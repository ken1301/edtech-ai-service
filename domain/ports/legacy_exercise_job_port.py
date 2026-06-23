from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

ProgressReporter = Callable[[dict[str, Any]], Awaitable[None]]


class LegacyExerciseJobPort(ABC):
    """Abstract contract for processing legacy BullMQ exercise extraction jobs."""

    @abstractmethod
    async def process_job(
        self,
        *,
        job_id: str,
        payload: Mapping[str, Any],
        progress_reporter: ProgressReporter | None = None,
    ) -> dict[str, Any]:
        """Process a legacy exercise job payload and return a JSON-serializable result."""
        raise NotImplementedError