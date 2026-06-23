import unittest
from types import SimpleNamespace

from application.use_cases.create_lesson_usecase import CreateLessonUseCase
from domain.exceptions import CloudManagerError, CreateLessonUseCaseError, DocumentTransformationError
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
from domain.models.overall_models.document import ImageDocument, MarkdownDocument, PDFDocument
from domain.models.overall_models.lesson1 import (
    CreateLessonMetadata,
    Exercise,
    ExerciseType,
    HookType,
    KnowledgeItem,
    Lesson1CreationOutput,
    Lesson1Knowledge,
    Lesson1StoredArtifact,
    Lesson1StoredSection,
    Lesson1Summary,
    Lesson2StoredArtifact,
)
from domain.models.overall_models.response import Lesson2ExerciseExtractionOutput
from domain.models.overall_models.token_usage import TokenUsage


def _lesson1_output() -> Lesson1CreationOutput:
    return Lesson1CreationOutput(
        user_id="user-1",
        knowledge=Lesson1Knowledge(
            concept_name="functions",
            hook_type=HookType.real_world,
            hook="Hook",
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
    )


def _lesson2_output() -> Lesson2Exercise:
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
    problem_list = []
    for index, role in enumerate(roles, start=1):
        problem_list.append(
            Problem(
                problem_id=index,
                question=f"Question {index}",
                attachment_url=[],
                approach_list=[
                    Approach(
                        summary=f"Approach {index}",
                        bloom_level=BloomLevel.APPLY,
                        concept_type_used=[ConceptType.METHOD],
                        pattern=ExercisePattern(
                            cognitive_operation=[CognitiveOperation.APPLY],
                            representation=[Representation.VERBAL],
                            constraints=[Constraint.NONE],
                        ),
                        approach_answer=f"Answer {index}",
                        strengths=[ApproachStrength.EASY_TO_IMPLEMENT],
                        weaknesses=[ApproachWeakness.CASE_SPECIFIC],
                        max_attempts=3,
                    )
                ],
                final_answer=f"Final {index}",
                open_approach=False,
                recommended_problem_role=role,
                max_approach_trial=2,
            )
        )

    return Lesson2Exercise(
        problem_list=problem_list,
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


def _lesson1_artifact() -> Lesson1StoredArtifact:
    output = _lesson1_output()
    return Lesson1StoredArtifact(
        user_id="user-1",
        lesson1=Lesson1StoredSection(
            learning_content=output.knowledge,
            exercise=output.exercises,
            summary=output.summary,
        ),
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


class _CloudManagerStub:
    def __init__(self, document):
        self.document = document
        self.fetch_calls = []
        self.upload_calls = []

    async def fetch_document(self, document_url: str, user_id: str):
        self.fetch_calls.append((document_url, user_id))
        return self.document

    async def upload_document(self, document, user_id: str):
        self.upload_calls.append((document, user_id))
        return f"https://cdn.example/{document.filename}"


class _CloudManagerFailureStub:
    async def fetch_document(self, document_url: str, user_id: str):
        raise CloudManagerError("cloud down")

    async def upload_document(self, document, user_id: str):
        raise AssertionError("upload_document should not be called")


class _LessonManagerStub:
    def __init__(self, metadata=None, artifact_by_id=None):
        self.metadata = metadata
        self.save_calls = []
        self.get_calls = []
        self.save_exercise_calls = []
        self.artifact_by_id = artifact_by_id or {}
        self.get_artifact_calls = []
        self.attach_root_calls = []
        self.delete_metadata_calls = []

    async def save_lesson_creation_metadata(self, lesson_id: str, user_id: str, metadata: CreateLessonMetadata):
        self.save_calls.append((lesson_id, user_id, metadata))
        self.metadata = metadata

    async def get_lesson_creation_metadata(self, lesson_id: str, user_id: str):
        self.get_calls.append((lesson_id, user_id))
        return self.metadata

    async def save_exercise(self, exercise_id: str, user_id: str, exercise):
        self.save_exercise_calls.append((exercise_id, user_id, exercise))
        self.artifact_by_id[exercise_id] = exercise
        return True

    async def get_lesson_artifact(self, exercise_id: str, user_id: str):
        self.get_artifact_calls.append((exercise_id, user_id))
        return self.artifact_by_id.get(exercise_id)

    async def attach_root_lesson_id(self, exercise_id: str, user_id: str, root_lesson_id: str):
        self.attach_root_calls.append((exercise_id, user_id, root_lesson_id))
        return True

    async def delete_lesson_creation_metadata(self, lesson_id: str, user_id: str):
        self.delete_metadata_calls.append((lesson_id, user_id))
        self.metadata = None
        return True


def _metadata(summary: Lesson1Summary) -> CreateLessonMetadata:
    return CreateLessonMetadata(
        user_id="user-1",
        lesson_id="lesson-1",
        lesson1_exercise_id="lesson-1:lesson1",
        lesson1_summary=summary,
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
    )


class _PromptBuilderStub:
    def __init__(self):
        self.lesson1_calls = []
        self.lesson2_calls = []

    async def lesson1_document_extraction_prompt(self, **kwargs):
        self.lesson1_calls.append(kwargs)
        return "lesson1-prompt"

    async def lesson2_exercise_extraction_prompt(self, **kwargs):
        self.lesson2_calls.append(kwargs)
        return "lesson2-prompt"


class _LLMManagerStub:
    def __init__(self, content):
        self.content = content
        self.calls = []

    async def generate_response(self, *, system_prompt, messages, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "messages": messages,
                "response_model": response_model,
            }
        )
        return SimpleNamespace(
            content=self.content,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


class _PDFToMarkdownTransformerStub:
    def __init__(self, markdown_document=None, image_set=None):
        self.markdown_document = markdown_document
        self.image_set = image_set or []
        self.calls = []

    async def execute(self, pdf_document):
        self.calls.append(pdf_document)
        return self.markdown_document, list(self.image_set)


class _PDFToMarkdownTransformerFailureStub:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = []

    async def execute(self, pdf_document):
        self.calls.append(pdf_document)
        raise self.error


class CreateLessonUseCasePdfIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_lesson1_markdown_passthrough_skips_transformer(self):
        document = MarkdownDocument(
            id="doc-1",
            filename="lesson.md",
            content="Markdown body",
            parent_pdf_id=None,
        )
        cloud_manager = _CloudManagerStub(document)
        lesson_manager = _LessonManagerStub()
        prompt_builder = _PromptBuilderStub()
        llm_manager = _LLMManagerStub(_lesson1_output())
        transformer = _PDFToMarkdownTransformerStub()
        usecase = CreateLessonUseCase(
            llm_manager=llm_manager,
            cloud_manager=cloud_manager,
            lesson_manager=lesson_manager,
            prompt_builder=prompt_builder,
            pdf_to_markdown_transformer=transformer,
        )

        await usecase.lesson1_run(
            user_id="user-1",
            lesson_id="lesson-1",
            document_url="https://example.com/lesson.md",
            previous_lessons=[],
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
        )

        self.assertEqual(transformer.calls, [])
        self.assertEqual(prompt_builder.lesson1_calls[0]["content"], "Markdown body")
        self.assertEqual(cloud_manager.upload_calls, [])
        self.assertEqual(lesson_manager.save_calls[0][0:2], ("lesson-1", "user-1"))
        self.assertEqual(lesson_manager.save_exercise_calls[0][0:2], ("lesson-1:lesson1", "user-1"))
        self.assertIsInstance(lesson_manager.save_exercise_calls[0][2], Lesson1StoredArtifact)

    async def test_lesson1_pdf_without_images_uses_transformed_markdown_content(self):
        document = PDFDocument(
            id="doc-2",
            filename="lesson.pdf",
            content=b"%PDF-1.7",
            size_bytes=8,
        )
        markdown_document = MarkdownDocument(
            id="doc-2",
            filename="lesson.md",
            content="Converted markdown",
            parent_pdf_id="doc-2",
        )
        cloud_manager = _CloudManagerStub(document)
        lesson_manager = _LessonManagerStub()
        prompt_builder = _PromptBuilderStub()
        llm_manager = _LLMManagerStub(_lesson1_output())
        transformer = _PDFToMarkdownTransformerStub(markdown_document=markdown_document)
        usecase = CreateLessonUseCase(
            llm_manager=llm_manager,
            cloud_manager=cloud_manager,
            lesson_manager=lesson_manager,
            prompt_builder=prompt_builder,
            pdf_to_markdown_transformer=transformer,
        )

        await usecase.lesson1_run(
            user_id="user-1",
            lesson_id="lesson-1",
            document_url="https://example.com/lesson.pdf",
            previous_lessons=[],
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
        )

        self.assertEqual(transformer.calls, [document])
        self.assertEqual(prompt_builder.lesson1_calls[0]["content"], "Converted markdown")
        self.assertEqual(cloud_manager.upload_calls, [])
        self.assertEqual(lesson_manager.save_calls[0][0:2], ("lesson-1", "user-1"))
        self.assertEqual(lesson_manager.save_exercise_calls[0][0:2], ("lesson-1:lesson1", "user-1"))

    async def test_lesson2_pdf_replaces_every_uploaded_image_reference(self):
        document = PDFDocument(
            id="doc-3",
            filename="lesson.pdf",
            content=b"%PDF-1.7",
            size_bytes=8,
        )
        markdown_document = MarkdownDocument(
            id="doc-3",
            filename="lesson.md",
            content="Intro ![one](img-1.png) middle ![two](img-2.png)",
            parent_pdf_id="doc-3",
        )
        image_set = [
            ImageDocument(id="img-1", filename="img-1.png", content=b"1", parent_pdf_id="doc-3"),
            ImageDocument(id="img-2", filename="img-2.png", content=b"2", parent_pdf_id="doc-3"),
        ]
        summary = Lesson1Summary(
            text="Summary text",
            core_skills=["trace function calls"],
            ready_for_problem_1=True,
        )
        cloud_manager = _CloudManagerStub(document)
        lesson_manager = _LessonManagerStub(
            metadata=_metadata(summary),
            artifact_by_id={"lesson-1:lesson1": _lesson1_artifact()},
        )
        prompt_builder = _PromptBuilderStub()
        llm_manager = _LLMManagerStub(_lesson2_output())
        transformer = _PDFToMarkdownTransformerStub(
            markdown_document=markdown_document,
            image_set=image_set,
        )
        usecase = CreateLessonUseCase(
            llm_manager=llm_manager,
            cloud_manager=cloud_manager,
            lesson_manager=lesson_manager,
            prompt_builder=prompt_builder,
            pdf_to_markdown_transformer=transformer,
        )

        response = await usecase.lesson2_run(
            user_id="user-1",
            lesson_id="lesson-1",
            document_url="https://example.com/lesson.pdf",
            subject=Subject.IT,
            topic=Topic.PROGRAMMING,
            concept=Concept.FUNCTIONS,
        )

        self.assertEqual(transformer.calls, [document])
        self.assertEqual(len(cloud_manager.upload_calls), 2)
        self.assertEqual(
            prompt_builder.lesson2_calls[0]["content"],
            "Intro ![one](https://cdn.example/img-1.png) middle ![two](https://cdn.example/img-2.png)",
        )
        self.assertEqual(prompt_builder.lesson2_calls[0]["lesson1_summary"], summary)
        self.assertIsInstance(response.output, Lesson2ExerciseExtractionOutput)
        self.assertEqual(response.output.exercise.user_id, "user-1")
        self.assertIn("Generated 8 lesson 2 problems", response.output.summary)
        self.assertEqual(response.exercise_id, "lesson-1")
        self.assertEqual(lesson_manager.save_exercise_calls[0][0:2], ("lesson-1", "user-1"))
        self.assertIsInstance(lesson_manager.save_exercise_calls[0][2], Lesson2StoredArtifact)
        self.assertEqual(
            lesson_manager.save_exercise_calls[0][2].lesson1,
            _lesson1_artifact().lesson1,
        )
        self.assertEqual(lesson_manager.save_exercise_calls[0][2].lesson2.exercise, response.output.exercise)
        self.assertEqual(lesson_manager.save_calls[-1][2].lesson2_exercise_id, "lesson-1")

    async def test_lesson1_cloud_failure_maps_to_specific_usecase_error(self):
        lesson_manager = _LessonManagerStub()
        prompt_builder = _PromptBuilderStub()
        llm_manager = _LLMManagerStub(_lesson1_output())
        transformer = _PDFToMarkdownTransformerStub()
        usecase = CreateLessonUseCase(
            llm_manager=llm_manager,
            cloud_manager=_CloudManagerFailureStub(),
            lesson_manager=lesson_manager,
            prompt_builder=prompt_builder,
            pdf_to_markdown_transformer=transformer,
        )

        with self.assertRaises(CreateLessonUseCaseError) as context:
            await usecase.lesson1_run(
                user_id="user-1",
                lesson_id="lesson-1",
                document_url="https://example.com/lesson.pdf",
                previous_lessons=[],
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
            )

        self.assertEqual(str(context.exception), "Failed to fetch document from cloud storage.")

    async def test_lesson1_transform_failure_maps_to_specific_usecase_error(self):
        document = PDFDocument(
            id="doc-4",
            filename="lesson.pdf",
            content=b"%PDF-1.7",
            size_bytes=8,
        )
        cloud_manager = _CloudManagerStub(document)
        lesson_manager = _LessonManagerStub()
        prompt_builder = _PromptBuilderStub()
        llm_manager = _LLMManagerStub(_lesson1_output())
        transformer = _PDFToMarkdownTransformerFailureStub(
            DocumentTransformationError("transform failed")
        )
        usecase = CreateLessonUseCase(
            llm_manager=llm_manager,
            cloud_manager=cloud_manager,
            lesson_manager=lesson_manager,
            prompt_builder=prompt_builder,
            pdf_to_markdown_transformer=transformer,
        )

        with self.assertRaises(CreateLessonUseCaseError) as context:
            await usecase.lesson1_run(
                user_id="user-1",
                lesson_id="lesson-1",
                document_url="https://example.com/lesson.pdf",
                previous_lessons=[],
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
            )

        self.assertEqual(str(context.exception), "Failed to transform document to Markdown format.")

    async def test_finalize_promotes_saved_exercises_and_deletes_metadata(self):
        summary = Lesson1Summary(
            text="Summary text",
            core_skills=["trace function calls"],
            ready_for_problem_1=True,
        )
        metadata = _metadata(summary)
        metadata.lesson2_exercise_id = "lesson-1"
        lesson_manager = _LessonManagerStub(metadata=metadata)
        usecase = CreateLessonUseCase(
            llm_manager=_LLMManagerStub(_lesson1_output()),
            cloud_manager=_CloudManagerStub(MarkdownDocument(id="doc", filename="x.md", content="x", parent_pdf_id=None)),
            lesson_manager=lesson_manager,
            prompt_builder=_PromptBuilderStub(),
            pdf_to_markdown_transformer=_PDFToMarkdownTransformerStub(),
        )

        response = await usecase.finalize_run(user_id="user-1", lesson_id="lesson-1")

        self.assertEqual(response.status, "published")
        self.assertEqual(
            lesson_manager.attach_root_calls,
            [
                ("lesson-1:lesson1", "user-1", "lesson-1"),
                ("lesson-1", "user-1", "lesson-1"),
            ],
        )
        self.assertEqual(lesson_manager.delete_metadata_calls, [("lesson-1", "user-1")])

    async def test_finalize_requires_lesson2_completion(self):
        summary = Lesson1Summary(
            text="Summary text",
            core_skills=["trace function calls"],
            ready_for_problem_1=True,
        )
        lesson_manager = _LessonManagerStub(metadata=_metadata(summary))
        usecase = CreateLessonUseCase(
            llm_manager=_LLMManagerStub(_lesson1_output()),
            cloud_manager=_CloudManagerStub(MarkdownDocument(id="doc", filename="x.md", content="x", parent_pdf_id=None)),
            lesson_manager=lesson_manager,
            prompt_builder=_PromptBuilderStub(),
            pdf_to_markdown_transformer=_PDFToMarkdownTransformerStub(),
        )

        with self.assertRaises(CreateLessonUseCaseError) as context:
            await usecase.finalize_run(user_id="user-1", lesson_id="lesson-1")

        self.assertEqual(str(context.exception), "Lesson 2 must be completed before publishing this lesson.")