import unittest

from adapters.outbound.cache.redis_lesson_adapter import RedisLessonAdapter
from adapters.outbound.persistence.mongo_lesson_store import MongoLessonAdapter
from domain.models.lesson2_models.exercise import Approach, Exercise, ExercisePattern, Problem
from domain.models.overall_models.common import BloomLevel, ConceptType, Constraint, ProblemRole, Representation
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.lesson1 import (
    CreateLessonMetadata,
    Lesson1StoredArtifact,
    Lesson1StoredSection,
    Lesson1Summary,
    Lesson2StoredArtifact,
    Lesson2StoredSection,
)


class _FakeRedis:
    def __init__(self):
        self.store = {}
        self.set_calls = []

    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted


class _FakeUpdateResult:
    acknowledged = True


class _FakeDeleteResult:
    deleted_count = 1


class _FakeCollection:
    def __init__(self):
        self.create_index_calls = []
        self.update_one_calls = []
        self.find_one_calls = []
        self.delete_one_calls = []
        self.find_one_result = None

    async def create_index(self, keys, unique=False, name=None, **kwargs):
        self.create_index_calls.append((keys, unique, name, kwargs))
        return name or 'idx'

    async def update_one(self, query, update, upsert=False):
        self.update_one_calls.append((query, update, upsert))
        return _FakeUpdateResult()

    async def find_one(self, query):
        self.find_one_calls.append(query)
        return self.find_one_result

    async def delete_one(self, query):
        self.delete_one_calls.append(query)
        return _FakeDeleteResult()


class _FakeDb:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return self.collection


def _summary() -> Lesson1Summary:
    return Lesson1Summary(text="summary", core_skills=["skill"], ready_for_problem_1=True)


def _metadata() -> CreateLessonMetadata:
    return CreateLessonMetadata(
        user_id="user-1",
        lesson_id="lesson-1",
        lesson1_exercise_id="lesson-1:lesson1",
        lesson1_summary=_summary(),
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _exercise() -> Exercise:
    problems = []
    role_order = [
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
    ]
    for index in range(8):
        problems.append(
            Problem(
                problem_id=index + 1,
                question=f"Question {index + 1}",
                approach_list=[
                    Approach(
                        summary="Direct approach",
                        bloom_level=BloomLevel.APPLY,
                        concept_type_used=[ConceptType.METHOD],
                        pattern=ExercisePattern(
                            cognitive_operation=[],
                            representation=[Representation.SYMBOLIC],
                            constraints=[Constraint.NONE],
                        ),
                        approach_answer="answer",
                        strengths=[],
                        weaknesses=[],
                        max_attempts=2,
                    )
                ],
                final_answer="answer",
                open_approach=False,
                recommended_problem_role=role_order[index % len(role_order)],
                max_approach_trial=1,
            )
        )

    return Exercise(
        problem_list=problems,
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        user_id="user-1",
    )


def _lesson1_artifact() -> Lesson1StoredArtifact:
    return Lesson1StoredArtifact(
        user_id="user-1",
        lesson1=Lesson1StoredSection(
            learning_content={
                "concept_name": "functions",
                "hook_type": "real_world",
                "hook": "Hook",
                "items": [],
                "prerequisites": [],
            },
            exercise=[],
            summary=_summary(),
        ),
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _lesson2_artifact() -> Lesson2StoredArtifact:
    lesson1_artifact = _lesson1_artifact()
    return Lesson2StoredArtifact(
        user_id="user-1",
        lesson1=lesson1_artifact.lesson1,
        lesson2=Lesson2StoredSection(
            exercise=_exercise(),
            summary="Generated 8 lesson 2 problems for functions.",
        ),
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


class LessonStoreOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_redis_lesson_metadata_is_user_scoped(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis)
        metadata = _metadata()

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)
        saved = await adapter.get_lesson_creation_metadata("lesson-1", "user-1")
        missing = await adapter.get_lesson_creation_metadata("lesson-1", "user-2")

        self.assertIsNotNone(saved)
        self.assertEqual(saved.lesson_id, "lesson-1")
        self.assertIsNone(missing)

    async def test_redis_lesson_metadata_falls_back_to_durable_copy(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis, ttl=30)
        metadata = _metadata()

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)
        redis.store.pop("lesson_creation:user-1:lesson-1:metadata")

        recovered = await adapter.get_lesson_creation_metadata("lesson-1", "user-1")

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.lesson1_summary.text, "summary")
        self.assertIn("lesson_creation:user-1:lesson-1:metadata", redis.store)

    async def test_redis_lesson_metadata_save_writes_durable_copy_without_ttl(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis, ttl=30)
        metadata = _metadata()

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)

        self.assertEqual(
            redis.set_calls,
            [
                (
                    "lesson_creation:user-1:lesson-1:metadata",
                    metadata.model_dump_json(by_alias=True),
                    30,
                ),
                (
                    "lesson_creation:user-1:lesson-1:metadata:durable",
                    metadata.model_dump_json(by_alias=True),
                    None,
                ),
            ],
        )

    async def test_mongo_exercise_queries_include_user_scope(self):
        collection = _FakeCollection()
        collection.find_one_result = {
            "exercise_id": "exercise-1",
            "user_id": "user-1",
            **_lesson2_artifact().model_dump(mode="json", exclude_none=True),
        }
        adapter = MongoLessonAdapter(db=_FakeDb(collection))

        await adapter.save_exercise("exercise-1", "user-1", _lesson1_artifact())
        await adapter.get_lesson_artifact("exercise-1", "user-1")
        await adapter.get_exercise("exercise-1", "user-1")
        await adapter.attach_root_lesson_id("exercise-1", "user-1", "lesson-1")
        await adapter.delete_exercise("exercise-1", "user-1")

        self.assertEqual(
            collection.create_index_calls,
            [(
                [("user_id", 1), ("exercise_id", 1)],
                True,
                "user_id_exercise_id_unique",
                {
                    "partialFilterExpression": {
                        "user_id": {"$type": "string"},
                        "exercise_id": {"$type": "string"},
                    }
                },
            )],
        )
        self.assertEqual(collection.update_one_calls[0][0], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.update_one_calls[0][1]["$set"]["lesson1"], _lesson1_artifact().lesson1.model_dump(mode="json"))
        self.assertEqual(collection.update_one_calls[0][1]["$set"]["lesson2"], {})
        self.assertEqual(collection.update_one_calls[1][0], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.update_one_calls[1][1]["$set"]["root_lesson_id"], "lesson-1")
        self.assertEqual(collection.find_one_calls[0], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.find_one_calls[1], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.delete_one_calls[0], {"exercise_id": "exercise-1", "user_id": "user-1"})

    async def test_mongo_public_exercise_query_uses_published_lesson_lookup_without_user_scope(self):
        collection = _FakeCollection()
        collection.find_one_result = {
            "exercise_id": "lesson-1",
            "root_lesson_id": "lesson-1",
            "user_id": "teacher-1",
            **_lesson2_artifact().model_dump(mode="json", exclude_none=True),
        }
        adapter = MongoLessonAdapter(db=_FakeDb(collection))

        exercise = await adapter.get_public_exercise("lesson-1")

        self.assertIsNotNone(exercise)
        self.assertEqual(collection.find_one_calls[0], {
            "$or": [
                {"exercise_id": "lesson-1"},
                {"root_lesson_id": "lesson-1"},
            ],
            "lesson2.exercise": {"$exists": True},
        })

    async def test_mongo_public_exercise_can_resolve_backend_draft_id_via_lesson2_exercise_id(self):
        collection = _FakeCollection()
        published_doc = {
            "exercise_id": "lesson-1",
            "root_lesson_id": "lesson-1",
            "user_id": "teacher-1",
            **_lesson2_artifact().model_dump(mode="json", exclude_none=True),
        }

        async def _find_one(query):
            collection.find_one_calls.append(query)
            filters = query.get("$or", [])
            if {"exercise_id": "draft-1"} in filters and query.get("lesson2_exercise_id") == {"$type": "string"}:
                return {
                    "exercise_id": "draft-1",
                    "lesson2_exercise_id": "lesson-1",
                }
            if {"exercise_id": "lesson-1"} in filters and query.get("lesson2.exercise") == {"$exists": True}:
                return published_doc
            return None

        collection.find_one = _find_one
        adapter = MongoLessonAdapter(db=_FakeDb(collection))

        exercise = await adapter.get_public_exercise("draft-1")

        self.assertIsNotNone(exercise)
        self.assertEqual(collection.find_one_calls[0], {
            "$or": [
                {"exercise_id": "draft-1"},
                {"root_lesson_id": "draft-1"},
            ],
            "lesson2.exercise": {"$exists": True},
        })
        self.assertEqual(collection.find_one_calls[1], {
            "$or": [
                {"exercise_id": "draft-1"},
                {"root_lesson_id": "draft-1"},
            ],
            "lesson2_exercise_id": {"$type": "string"},
        })
        self.assertEqual(collection.find_one_calls[2], {
            "$or": [
                {"exercise_id": "lesson-1"},
                {"root_lesson_id": "lesson-1"},
            ],
            "lesson2.exercise": {"$exists": True},
        })

    async def test_redis_lesson_metadata_key_is_user_scoped(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis)
        metadata = _metadata()

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)

        self.assertIn("lesson_creation:user-1:lesson-1:metadata", redis.store)
        self.assertIn("lesson_creation:user-1:lesson-1:metadata:durable", redis.store)

    async def test_redis_lesson_metadata_delete_removes_primary_and_durable_keys(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis)
        metadata = _metadata()

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)
        deleted = await adapter.delete_lesson_creation_metadata("lesson-1", "user-1")

        self.assertTrue(deleted)
        self.assertNotIn("lesson_creation:user-1:lesson-1:metadata", redis.store)
        self.assertNotIn("lesson_creation:user-1:lesson-1:metadata:durable", redis.store)


if __name__ == "__main__":
    unittest.main()