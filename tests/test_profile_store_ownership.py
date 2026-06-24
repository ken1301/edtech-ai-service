import unittest
from bson import BSON

from adapters.outbound.persistence.mongo_profile_store import MongoProfileAdapter
from domain.models.overall_models.common import (
    ApproachStrength,
    ApproachWeakness,
    BloomLevel,
    CognitiveOperation,
    ConceptType,
    DifficultyLevel,
    ProblemRole,
    Representation,
    StudentStrength,
    StudentWeakness,
)
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.profile import (
    LearningDetail,
    LearningStyle,
    Performance,
    StudentPattern,
    StudentPreference,
)


class _FakeUpdateResult:
    acknowledged = True


class _FakeCollection:
    def __init__(self):
        self.update_one_calls = []

    async def update_one(self, query, update, upsert=False):
        self.update_one_calls.append((query, update, upsert))
        return _FakeUpdateResult()


class _FakeDb:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, name):
        return self.collection


class MongoProfileStoreOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_student_profile_serializes_nested_enums_for_mongo(self):
        collection = _FakeCollection()
        adapter = MongoProfileAdapter(_FakeDb(collection))

        student_preference = StudentPreference(
            summary="Prefers worked examples.",
            strengths=[StudentStrength.GOOD_LOGIC],
            weaknesses=[StudentWeakness.OVER_THINKING],
            learning_style=LearningStyle(
                cognitive_operation=[CognitiveOperation.ANALYZE],
                representation=[Representation.VERBAL],
            ),
            preferred_difficulty=DifficultyLevel.MEDIUM,
        )
        learning_detail = LearningDetail(
            avg_score=0.75,
            mastering_at=[ConceptType.DEFINITION],
            struggling_at=[ConceptType.VISUALIZATION],
            finished_exercise={
                ProblemRole.REINFORCEMENT: Performance(
                    score=0.9,
                    bloom_level=BloomLevel.APPLY,
                    strengths=[ApproachStrength.EASY_TO_IMPLEMENT],
                    weaknesses=[ApproachWeakness.HARD_TO_IMPLEMENT],
                    pattern=StudentPattern(
                        cognitive_operation=[CognitiveOperation.APPLY],
                        representation=[Representation.SYMBOLIC],
                    ),
                )
            },
        )

        await adapter.update_student_profile(
            user_id="user-1",
            subject=Subject.MATH,
            topic=Topic.LINEAR_ALGEBRA,
            concept=Concept.VECTORS,
            student_preference=student_preference,
            learning_detail=learning_detail,
        )

        self.assertEqual(len(collection.update_one_calls), 1)
        query, update, upsert = collection.update_one_calls[0]

        self.assertEqual(query, {"user_id": "user-1"})
        self.assertTrue(upsert)

        serialized_detail = update["$set"]["knowledge_map.math.linear_algebra.vectors"]
        serialized_preference = update["$set"]["preferences"]

        self.assertEqual(serialized_detail["mastering_at"], ["definition"])
        self.assertEqual(serialized_detail["struggling_at"], ["visualization"])
        self.assertIn("reinforcement", serialized_detail["finished_exercise"])
        self.assertEqual(
            serialized_detail["finished_exercise"]["reinforcement"]["strengths"],
            ["easy_to_implement"],
        )
        self.assertEqual(serialized_preference["preferred_difficulty"], "medium")
        self.assertEqual(serialized_preference["strengths"], ["good_logic"])

        BSON.encode(update)
