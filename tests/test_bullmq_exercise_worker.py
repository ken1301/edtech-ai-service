import unittest

from domain.exceptions import LegacyExerciseJobError
from domain.models.lesson2_models.common import Phase
from domain.models.lesson2_models.exercise import Approach, Exercise as Lesson2Exercise, ExercisePattern, Problem
from domain.models.overall_models.common import (
    ApproachStrength,
    ApproachWeakness,
    BloomLevel,
    CognitiveOperation,
    ConceptType,
    Constraint,
    ProblemRole,
    Representation,
)
from domain.models.overall_models.curriculum import Concept, Subject, Topic
from domain.models.overall_models.lesson1 import (
    Exercise,
    ExerciseType,
    HookType,
    KnowledgeItem,
    Lesson1CreationOutput,
    Lesson1Knowledge,
    Lesson1Summary,
)
from domain.models.overall_models.response import (
    Lesson1CreationResponse,
    Lesson2ExerciseExtractionOutput,
    Lesson2ExerciseExtractionResponse,
)
from domain.models.overall_models.token_usage import TokenUsage
from application.services.legacy_exercise_job_service import LegacyExerciseJobService
from adapters.inbound.queue.bullmq_worker import BullMQExerciseWorkerAdapter


def _legacy_payload(**overrides):
    payload = {
        "teacherId": "teacher-1",
        "classId": "class-1",
        "fileUrl": "https://example.com/lesson.pdf",
        "title": "Functions worksheet",
        "description": "Original description",
        "subject": "it",
        "topic": "programming",
        "concept": "functions",
    }
    payload.update(overrides)
    return payload


def _lesson1_response() -> Lesson1CreationResponse:
    return Lesson1CreationResponse(
        exercise_id="job-123:lesson1",
        output=Lesson1CreationOutput(
            user_id="teacher-1",
            knowledge=Lesson1Knowledge(
                concept_name="functions",
                hook_type=HookType.real_world,
                hook="Functions help reuse logic.",
                items=[
                    KnowledgeItem(
                        content_type=ConceptType.DEFINITION,
                        title="Definition",
                        content="A function groups reusable logic.",
                        is_core=True,
                        from_source=True,
                    )
                ],
                prerequisites=["variables"],
            ),
            exercises=[
                Exercise(
                    exercise_type=ExerciseType.SHORT_ANSWER,
                    question="What is a function?",
                    answer="Reusable logic",
                    explanation="Functions package behavior.",
                    concept_type_used=[ConceptType.DEFINITION],
                    bloom_level=BloomLevel.REMEMBER,
                    pdeo_phase=Phase.PROBLEM,
                    targets_problem_1=True,
                )
            ],
            summary=Lesson1Summary(
                text="Student can explain what functions are.",
                core_skills=["identify functions"],
                ready_for_problem_1=True,
            ),
        ),
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


def _lesson2_response() -> Lesson2ExerciseExtractionResponse:
    roles = [
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
    ]
    problems = []
    for index, role in enumerate(roles, start=1):
        problems.append(
            Problem(
                problem_id=index,
                question=f"Write function {index}",
                attachment_url=[],
                approach_list=[
                    Approach(
                        summary="Use def",
                        bloom_level=BloomLevel.APPLY,
                        concept_type_used=[ConceptType.METHOD],
                        pattern=ExercisePattern(
                            cognitive_operation=[CognitiveOperation.APPLY],
                            representation=[Representation.VERBAL],
                            constraints=[Constraint.NONE],
                        ),
                        approach_answer=f"def solve_{index}(a, b): return a + b",
                        strengths=[ApproachStrength.EASY_TO_IMPLEMENT],
                        weaknesses=[ApproachWeakness.CASE_SPECIFIC],
                        max_attempts=3,
                    )
                ],
                final_answer=f"def solve_{index}(a, b): return a + b",
                open_approach=False,
                recommended_problem_role=role,
                max_approach_trial=2,
            )
        )
    return Lesson2ExerciseExtractionResponse(
        exercise_id="job-123",
        output=Lesson2ExerciseExtractionOutput(
            exercise=Lesson2Exercise(
                problem_list=problems,
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                user_id="teacher-1",
            ),
            summary="Generated 1 lesson 2 problem for functions.",
        ),
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


class _LessonCreationManagerStub:
    def __init__(self):
        self.lesson1_calls = []
        self.lesson2_calls = []

    async def lesson1_run(self, **kwargs):
        self.lesson1_calls.append(kwargs)
        return _lesson1_response()

    async def lesson2_run(self, **kwargs):
        self.lesson2_calls.append(kwargs)
        return _lesson2_response()


class _ProgressAwareProcessorStub:
    def __init__(self):
        self.calls = []

    async def process_job(self, *, job_id, payload, progress_reporter=None):
        self.calls.append({"job_id": job_id, "payload": payload})
        if progress_reporter is not None:
            await progress_reporter({"status": "parsing", "progress": 30})
            await progress_reporter({"status": "parsing", "progress": 70})
        return {"lesson_id": job_id, "lesson2_exercise_id": "job-123"}


class _FakeJob:
    def __init__(self, *, job_id="job-123", name="extract-exercise", data=None):
        self.id = job_id
        self.name = name
        self.data = data or _legacy_payload()
        self.progress_updates = []

    async def updateProgress(self, payload):
        self.progress_updates.append(payload)


class LegacyExerciseJobServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_job_maps_legacy_payload_to_existing_use_case(self):
        manager = _LessonCreationManagerStub()
        service = LegacyExerciseJobService(lesson_creation_manager=manager)

        result = await service.process_job(
            job_id="job-123",
            payload=_legacy_payload(previousLessons=["variables", "control_flow"]),
        )

        self.assertEqual(manager.lesson1_calls[0]["lesson_id"], "job-123")
        self.assertEqual(manager.lesson2_calls[0]["lesson_id"], "job-123")
        self.assertEqual(
            manager.lesson1_calls[0]["previous_lessons"],
            [Concept.VARIABLES, Concept.CONTROL_FLOW],
        )
        self.assertEqual(result["lesson1_exercise_id"], "job-123:lesson1")
        self.assertEqual(result["lesson2_exercise_id"], "job-123")
        self.assertEqual(result["subject"], "it")
        self.assertEqual(len(result["problem_list"]), 8)
        self.assertIn("# functions", result["theory_markdown"])
        self.assertIn("## Lý thuyết bài học", result["description"])

    async def test_process_job_rejects_inconsistent_curriculum_path(self):
        manager = _LessonCreationManagerStub()
        service = LegacyExerciseJobService(lesson_creation_manager=manager)

        with self.assertRaises(LegacyExerciseJobError):
            await service.process_job(
                job_id="job-123",
                payload=_legacy_payload(subject="math", topic="programming", concept="functions"),
            )

    async def test_process_job_rejects_invalid_previous_lesson_concept(self):
        manager = _LessonCreationManagerStub()
        service = LegacyExerciseJobService(lesson_creation_manager=manager)

        with self.assertRaises(LegacyExerciseJobError):
            await service.process_job(
                job_id="job-123",
                payload=_legacy_payload(previous_lessons=["not-a-concept"]),
            )


class BullMQExerciseWorkerAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_job_updates_progress_and_returns_processor_result(self):
        processor = _ProgressAwareProcessorStub()
        adapter = BullMQExerciseWorkerAdapter(
            job_processor=processor,
            redis_url="redis://localhost:6379/0",
            redis_password=None,
            queue_name="exercises",
            job_name="extract-exercise",
            prefix="bull",
            concurrency=1,
            worker_name="ai-service",
        )
        job = _FakeJob()

        result = await adapter._process_job(job)

        self.assertEqual(result["lesson_id"], "job-123")
        self.assertEqual(job.progress_updates[0], {"status": "parsing", "progress": 10})
        self.assertEqual(job.progress_updates[1], {"status": "parsing", "progress": 30})
        self.assertEqual(job.progress_updates[2], {"status": "parsing", "progress": 70})
        self.assertEqual(job.progress_updates[3]["status"], "done")

    async def test_process_job_rejects_unexpected_job_name(self):
        processor = _ProgressAwareProcessorStub()
        adapter = BullMQExerciseWorkerAdapter(
            job_processor=processor,
            redis_url="redis://localhost:6379/0",
            redis_password=None,
            queue_name="exercises",
            job_name="extract-exercise",
            prefix="bull",
            concurrency=1,
            worker_name="ai-service",
        )
        job = _FakeJob(name="wrong-job")

        with self.assertRaises(ValueError):
            await adapter._process_job(job)

        self.assertEqual(job.progress_updates[-1]["status"], "error")