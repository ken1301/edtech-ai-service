import unittest

from adapters.outbound.cache.redis_lesson_adapter import RedisLessonAdapter
from adapters.outbound.persistence.mongo_exercise_store import MongoExerciseAdapter
from domain.models.lesson2_models.exercise import Approach, Exercise, ExercisePattern, Problem
from domain.models.overall_models.common import BloomLevel, ConceptType, Constraint, ProblemRole, Representation
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.lesson1 import CreateLessonMetadata, Lesson1Summary


class _FakeRedis:
    def __init__(self):
        self.store = {}
        self.set_calls = []

    async def set(self, key, value, ex=None):
        self.set_calls.append((key, value, ex))
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)


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


class LessonStoreOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_redis_lesson_metadata_is_user_scoped(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis)
        metadata = CreateLessonMetadata(lesson_id="lesson-1", lesson1_summary=_summary())

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)
        saved = await adapter.get_lesson_creation_metadata("lesson-1", "user-1")
        missing = await adapter.get_lesson_creation_metadata("lesson-1", "user-2")

        self.assertIsNotNone(saved)
        self.assertEqual(saved.lesson_id, "lesson-1")
        self.assertIsNone(missing)

    async def test_redis_lesson_metadata_falls_back_to_durable_copy(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis, ttl=30)
        metadata = CreateLessonMetadata(lesson_id="lesson-1", lesson1_summary=_summary())

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)
        redis.store.pop("lesson_creation:user-1:lesson-1:metadata")

        recovered = await adapter.get_lesson_creation_metadata("lesson-1", "user-1")

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.lesson1_summary.text, "summary")
        self.assertIn("lesson_creation:user-1:lesson-1:metadata", redis.store)

    async def test_redis_lesson_metadata_save_writes_durable_copy_without_ttl(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis, ttl=30)
        metadata = CreateLessonMetadata(lesson_id="lesson-1", lesson1_summary=_summary())

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
        collection.find_one_result = {"exercise": _exercise().model_dump(mode="json")}
        adapter = MongoExerciseAdapter(db=_FakeDb(collection))

        await adapter.save_exercise("exercise-1", "user-1", _exercise())
        await adapter.get_exercise("exercise-1", "user-1")
        await adapter.delete_exercise("exercise-1", "user-1")

        self.assertEqual(
            collection.create_index_calls,
            [(
                [("user_id", 1), ("exercise_id", 1)],
                True,
                "user_id_exercise_id_unique",
                {
                    "partialFilterExpression": {
                        "user_id": {"$exists": True, "$ne": None},
                        "exercise_id": {"$exists": True, "$ne": None},
                    }
                },
            )],
        )
        self.assertEqual(collection.update_one_calls[0][0], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.find_one_calls[0], {"exercise_id": "exercise-1", "user_id": "user-1"})
        self.assertEqual(collection.delete_one_calls[0], {"exercise_id": "exercise-1", "user_id": "user-1"})

    async def test_redis_lesson_metadata_key_is_user_scoped(self):
        redis = _FakeRedis()
        adapter = RedisLessonAdapter(redis_client=redis)
        metadata = CreateLessonMetadata(lesson_id="lesson-1", lesson1_summary=_summary())

        await adapter.save_lesson_creation_metadata("lesson-1", "user-1", metadata)

        self.assertIn("lesson_creation:user-1:lesson-1:metadata", redis.store)
        self.assertIn("lesson_creation:user-1:lesson-1:metadata:durable", redis.store)


if __name__ == "__main__":
    unittest.main()