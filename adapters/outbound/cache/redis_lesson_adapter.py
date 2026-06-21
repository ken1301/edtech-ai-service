import json

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from domain.ports.lesson_store_port import LessonStorePort

from domain.models.overall_models.lesson1 import CreateLessonMetadata

from domain.exceptions import LessonStoreError

from infrastructure.logging import logger

class RedisLessonAdapter(LessonStorePort):
    _META_KEY_TPL = "lesson_creation:{lesson_id}:metadata"
    _DEFAULT_TTL  = 60 * 60 * 2  # 2 h  — Redis key expiry

    def __init__(
        self,
        redis_client: aioredis.Redis,
        ttl: int = _DEFAULT_TTL,
    ):
        self._redis = redis_client
        self._ttl = ttl

    def _meta_key(self, lesson_id: str) -> str:
        return self._META_KEY_TPL.format(lesson_id=lesson_id)

    async def save_lesson_creation_metadata(
        self,
        lesson_id: str,
        metadata: CreateLessonMetadata,
    ) -> bool:
        try:
            await self._redis.set(
                self._meta_key(lesson_id),
                metadata.model_dump_json(),
                ex=self._ttl,
            )
            logger.debug(
                "redis_lesson_adapter.save_lesson_creation_metadata.completed",
                log_type="debug",
                lesson_id=lesson_id,
            )
            return True

        except RedisError as e:
            logger.error(
                "redis_lesson_adapter.save_lesson_creation_metadata.failed",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Failed to save lesson creation metadata for lesson '{lesson_id}' to Redis."
            ) from e

        except Exception as e:
            logger.error(
                "redis_lesson_adapter.save_lesson_creation_metadata.unexpected_error",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonStoreError(
                "An unexpected error occurred while saving lesson creation metadata."
            ) from e

    async def get_lesson_creation_metadata(
        self,
        lesson_id: str,
    ) -> CreateLessonMetadata:
        try:
            raw = await self._redis.get(self._meta_key(lesson_id))
        except RedisError as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.failed",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Failed to fetch lesson creation metadata for lesson '{lesson_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.unexpected_error",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonStoreError(
                "An unexpected error occurred while fetching lesson creation metadata."
            ) from e

        if not raw:
            logger.debug(
                "redis_lesson_adapter.get_lesson_creation_metadata.not_found",
                log_type="debug",
                lesson_id=lesson_id,
            )
            return None

        try:
            data = json.loads(raw)
            metadata = CreateLessonMetadata(**data)
        except json.JSONDecodeError as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.deserialize_failed",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Corrupt lesson metadata JSON for lesson '{lesson_id}'."
            ) from e
        except Exception as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.invalid_payload",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Invalid lesson metadata for lesson '{lesson_id}'."
            ) from e

        logger.debug(
            "redis_lesson_adapter.get_lesson_creation_metadata.completed",
            log_type="debug",
            lesson_id=lesson_id,
        )
        return metadata

    # --- Methods not implemented in Redis adapter, but required by LessonStorePort interface ---
    async def save_exercise(self, *args, **kwargs):
        raise NotImplementedError("save_exercise is a MongoDB operation.")

    async def get_exercise(self, *args, **kwargs):
        raise NotImplementedError("get_exercise is a MongoDB operation.")

    async def delete_exercise(self, *args, **kwargs):
        raise NotImplementedError("delete_exercise is a MongoDB operation.")