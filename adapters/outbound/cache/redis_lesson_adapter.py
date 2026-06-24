import json

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from domain.ports.lesson_store_port import LessonStorePort

from domain.models.overall_models.lesson1 import CreateLessonMetadata

from domain.exceptions import LessonStoreError

from infrastructure.logging import logger

class RedisLessonAdapter(LessonStorePort):
    _META_KEY_TPL = "lesson_creation:{user_id}:{lesson_id}:metadata"
    _DURABLE_META_KEY_TPL = "lesson_creation:{user_id}:{lesson_id}:metadata:durable"
    _DEFAULT_TTL  = 60 * 60 * 2  # 2 h  — Redis key expiry

    def __init__(
        self,
        redis_client: aioredis.Redis,
        ttl: int = _DEFAULT_TTL,
    ):
        self._redis = redis_client
        self._ttl = ttl

    def _meta_key(self, lesson_id: str, user_id: str) -> str:
        return self._META_KEY_TPL.format(user_id=user_id, lesson_id=lesson_id)

    def _durable_meta_key(self, lesson_id: str, user_id: str) -> str:
        return self._DURABLE_META_KEY_TPL.format(user_id=user_id, lesson_id=lesson_id)

    async def save_lesson_creation_metadata(
        self,
        lesson_id: str,
        user_id: str,
        metadata: CreateLessonMetadata,
    ) -> bool:
        try:
            payload = metadata.model_dump_json(by_alias=True)
            await self._redis.set(
                self._meta_key(lesson_id, user_id),
                payload,
                ex=self._ttl,
            )
            await self._redis.set(
                self._durable_meta_key(lesson_id, user_id),
                payload,
            )
            logger.debug(
                "redis_lesson_adapter.save_lesson_creation_metadata.completed",
                log_type="debug",
                lesson_id=lesson_id,
                user_id=user_id,
            )
            return True

        except RedisError as e:
            logger.error(
                "redis_lesson_adapter.save_lesson_creation_metadata.failed",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
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
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonStoreError(
                "An unexpected error occurred while saving lesson creation metadata."
            ) from e

    async def get_lesson_creation_metadata(
        self,
        lesson_id: str,
        user_id: str,
    ) -> CreateLessonMetadata:
        try:
            primary_key = self._meta_key(lesson_id, user_id)
            durable_key = self._durable_meta_key(lesson_id, user_id)
            raw = await self._redis.get(primary_key)
        except RedisError as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.failed",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
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
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonStoreError(
                "An unexpected error occurred while fetching lesson creation metadata."
            ) from e

        if not raw:
            try:
                raw = await self._redis.get(durable_key)
            except RedisError as e:
                logger.error(
                    "redis_lesson_adapter.get_lesson_creation_metadata.durable_failed",
                    log_type="technical",
                    lesson_id=lesson_id,
                    user_id=user_id,
                    error=str(e),
                )
                raise LessonStoreError(
                    f"Failed to fetch durable lesson creation metadata for lesson '{lesson_id}' from Redis."
                ) from e
            except Exception as e:
                logger.error(
                    "redis_lesson_adapter.get_lesson_creation_metadata.durable_unexpected_error",
                    log_type="technical",
                    lesson_id=lesson_id,
                    user_id=user_id,
                    error=str(e),
                    exc_info=True,
                )
                raise LessonStoreError(
                    "An unexpected error occurred while fetching durable lesson creation metadata."
                ) from e

            if not raw:
                logger.debug(
                    "redis_lesson_adapter.get_lesson_creation_metadata.not_found",
                    log_type="debug",
                    lesson_id=lesson_id,
                    user_id=user_id,
                )
                return None

            logger.info(
                "redis_lesson_adapter.get_lesson_creation_metadata.recovered_from_durable",
                log_type="business",
                lesson_id=lesson_id,
                user_id=user_id,
            )
            try:
                await self._redis.set(primary_key, raw, ex=self._ttl)
            except RedisError:
                logger.warning(
                    "redis_lesson_adapter.get_lesson_creation_metadata.rehydrate_failed",
                    log_type="technical",
                    lesson_id=lesson_id,
                    user_id=user_id,
                )

        try:
            data = json.loads(raw)
            metadata = CreateLessonMetadata(**data)
        except json.JSONDecodeError as e:
            logger.error(
                "redis_lesson_adapter.get_lesson_creation_metadata.deserialize_failed",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
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
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Invalid lesson metadata for lesson '{lesson_id}'."
            ) from e

        logger.debug(
            "redis_lesson_adapter.get_lesson_creation_metadata.completed",
            log_type="debug",
            lesson_id=lesson_id,
            user_id=user_id,
        )
        return metadata

    async def delete_lesson_creation_metadata(self, lesson_id: str, user_id: str) -> bool:
        try:
            deleted = await self._redis.delete(
                self._meta_key(lesson_id, user_id),
                self._durable_meta_key(lesson_id, user_id),
            )
            logger.debug(
                "redis_lesson_adapter.delete_lesson_creation_metadata.completed",
                log_type="debug",
                lesson_id=lesson_id,
                user_id=user_id,
            )
            return bool(deleted)
        except RedisError as e:
            logger.error(
                "redis_lesson_adapter.delete_lesson_creation_metadata.failed",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Failed to delete lesson creation metadata for lesson '{lesson_id}' from Redis."
            ) from e
        except Exception as e:
            logger.error(
                "redis_lesson_adapter.delete_lesson_creation_metadata.unexpected_error",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonStoreError(
                "An unexpected error occurred while deleting lesson creation metadata."
            ) from e

    # --- Methods not implemented in Redis adapter, but required by LessonStorePort interface ---
    async def save_exercise(self, *args, **kwargs):
        raise NotImplementedError("save_exercise is a MongoDB operation.")

    async def get_lesson_artifact(self, *args, **kwargs):
        raise NotImplementedError("get_lesson_artifact is a MongoDB operation.")

    async def get_exercise(self, *args, **kwargs):
        raise NotImplementedError("get_exercise is a MongoDB operation.")

    async def get_public_exercise(self, *args, **kwargs):
        raise NotImplementedError("get_public_exercise is a MongoDB operation.")

    async def delete_exercise(self, *args, **kwargs):
        raise NotImplementedError("delete_exercise is a MongoDB operation.")

    async def attach_root_lesson_id(self, *args, **kwargs):
        raise NotImplementedError("attach_root_lesson_id is a MongoDB operation.")