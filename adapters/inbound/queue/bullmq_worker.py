from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

try:
    from bullmq import Worker
except ModuleNotFoundError as import_error:
    Worker = None
    _BULLMQ_IMPORT_ERROR = import_error
else:
    _BULLMQ_IMPORT_ERROR = None

from infrastructure.logging import logger


class BullMQExerciseWorkerAdapter:
    """Inbound adapter that consumes legacy exercise jobs from BullMQ."""

    def __init__(
        self,
        *,
        job_processor,
        redis_url: str,
        redis_password: str | None,
        queue_name: str,
        job_name: str,
        prefix: str,
        concurrency: int,
        worker_name: str,
    ):
        self._job_processor = job_processor
        self._redis_url = redis_url
        self._redis_password = redis_password
        self._queue_name = queue_name
        self._job_name = job_name
        self._prefix = prefix
        self._concurrency = concurrency
        self._worker_name = worker_name
        self._worker: Worker | None = None

    async def start(self) -> None:
        if self._worker is not None:
            return

        if Worker is None:
            raise ModuleNotFoundError(
                "bullmq is required to start the legacy BullMQ worker. Install project dependencies before running ai-service-bullmq-worker."
            ) from _BULLMQ_IMPORT_ERROR

        self._worker = Worker(
            self._queue_name,
            self._process_job,
            {
                "connection": self._build_connection_options(),
                "prefix": self._prefix,
                "concurrency": self._concurrency,
                "name": self._worker_name,
            },
        )
        logger.info(
            "bullmq_exercise_worker.started",
            log_type="business",
            queue_name=self._queue_name,
            job_name=self._job_name,
            prefix=self._prefix,
            concurrency=self._concurrency,
            worker_name=self._worker_name,
        )

    async def close(self) -> None:
        if self._worker is None:
            return

        await self._worker.close()
        self._worker = None
        logger.info(
            "bullmq_exercise_worker.closed",
            log_type="business",
            queue_name=self._queue_name,
            worker_name=self._worker_name,
        )

    async def _process_job(self, job, token=None) -> dict[str, Any]:
        job_id = str(job.id or uuid4())

        if job.name != self._job_name:
            error_message = (
                f"Unsupported BullMQ job name '{job.name}'. Expected '{self._job_name}'."
            )
            await job.updateProgress({"status": "error", "progress": 0, "error": error_message})
            raise ValueError(error_message)

        await job.updateProgress({"status": "parsing", "progress": 10})

        try:
            result = await self._job_processor.process_job(
                job_id=job_id,
                payload=job.data,
                progress_reporter=job.updateProgress,
            )
        except Exception as exc:
            logger.error(
                "bullmq_exercise_worker.process.failed",
                log_type="technical",
                queue_name=self._queue_name,
                job_name=job.name,
                job_id=job_id,
                error=str(exc),
                exc_info=True,
            )
            await job.updateProgress({"status": "error", "progress": 0, "error": str(exc)})
            raise

        await job.updateProgress(
            {
                "status": "done",
                "progress": 100,
                "lessonId": result.get("lesson_id"),
                "exerciseId": result.get("lesson2_exercise_id"),
            }
        )
        return result

    def _build_connection_options(self) -> dict[str, Any]:
        parsed = urlparse(self._redis_url)
        database_path = parsed.path.lstrip("/")
        connection: dict[str, Any] = {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 6379,
            "db": int(database_path or 0),
        }

        password = parsed.password or self._redis_password
        if password:
            connection["password"] = password
        if parsed.username:
            connection["username"] = parsed.username
        if parsed.scheme == "rediss":
            connection["ssl"] = True

        return connection