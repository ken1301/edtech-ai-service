import asyncio
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from typing import List, Optional

from application.services.cloud_manager import CloudManager
from application.services.lesson_manager import LessonManager

from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.docs_transform import PDFToMarkdownTransformer

from domain.models.lesson2_models.exercise import Exercise, Lesson2Exercises
from domain.models.overall_models.document import ImageDocument, MarkdownDocument, PDFDocument
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.response import (
    FinalizeLessonResponse,
    Lesson2ExerciseExtractionOutput,
    Lesson2ExerciseExtractionResponse,
    Lesson1CreationResponse,
)
from domain.models.overall_models.lesson1 import (
    CreateLessonMetadata,
    Lesson1CreationOutput,
    Lesson1StoredArtifact,
    Lesson1StoredSection,
    Lesson2StoredArtifact,
    Lesson2StoredSection,
)

from domain.exceptions import (
    LLMManagerError,
    CloudManagerError,
    PromptGenerationError,
    ProfileManagerError,
    LessonManagerError,
    DocumentTransformationError,
    ProblemSelectionAnalysisError,
    CreateLessonUseCaseError
)

from infrastructure.logging import logger

# old name: CreateLessonUseCase
class CreateLessonUseCase:
    """Use case responsible for selecting appropriate exercises based on the provided document and user context."""

    def __init__(
        self,
        llm_manager: LLMManager,
        cloud_manager: CloudManager,
        lesson_manager: LessonManager,
        prompt_builder: PromptBuilder,
        pdf_to_markdown_transformer: PDFToMarkdownTransformer,
    ):
        self._llm_manager = llm_manager
        self._cloud_manager = cloud_manager
        self._lesson_manager = lesson_manager 
        self._prompt_builder = prompt_builder
        self._pdf_to_markdown_transformer = pdf_to_markdown_transformer

    @staticmethod
    def _lesson1_exercise_id(lesson_id: str) -> str:
        return f"{lesson_id}:lesson1"

    @staticmethod
    def _summarize_lesson2_exercise(exercise: Exercise) -> str:
        total_problems = len(exercise.problem_list)
        leading_roles = ", ".join(
            problem.recommended_problem_role.value for problem in exercise.problem_list[:4]
        )
        if not leading_roles:
            leading_roles = "none"
        return (
            f"Generated {total_problems} lesson 2 problems for {exercise.concept.value} "
            f"with leading roles: {leading_roles}."
        )

    async def finalize_run(self, user_id: str, lesson_id: str) -> FinalizeLessonResponse:
        try:
            lesson_creation_metadata = await self._lesson_manager.get_lesson_creation_metadata(
                lesson_id=lesson_id,
                user_id=user_id,
            )
            if lesson_creation_metadata is None:
                raise CreateLessonUseCaseError("Lesson creation metadata was not found.")
            if not lesson_creation_metadata.lesson2_exercise_id:
                raise CreateLessonUseCaseError("Lesson 2 must be completed before publishing this lesson.")

            await self._lesson_manager.attach_root_lesson_id(
                exercise_id=lesson_creation_metadata.lesson1_exercise_id,
                user_id=user_id,
                root_lesson_id=lesson_id,
            )
            await self._lesson_manager.attach_root_lesson_id(
                exercise_id=lesson_creation_metadata.lesson2_exercise_id,
                user_id=user_id,
                root_lesson_id=lesson_id,
            )
            await self._lesson_manager.delete_lesson_creation_metadata(
                lesson_id=lesson_id,
                user_id=user_id,
            )

            return FinalizeLessonResponse(
                status="published",
                lesson_id=lesson_id,
                lesson1_exercise_id=lesson_creation_metadata.lesson1_exercise_id,
                lesson2_exercise_id=lesson_creation_metadata.lesson2_exercise_id,
            )
        except CreateLessonUseCaseError:
            raise
        except LessonManagerError as e:
            raise CreateLessonUseCaseError("Failed to finalize lesson publication state.") from e
        except Exception as e:
            logger.error(
                "create_lesson.finalize.unexpected.failed",
                log_type="technical",
                lesson_id=lesson_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Unexpected error during lesson finalization process.") from e

    async def _load_document_content(
        self,
        *,
        user_id: str,
        document_url: str,
        no_images_log_event: str,
    ) -> str:
        document = await self._cloud_manager.fetch_document(document_url=document_url, user_id=user_id)
        if isinstance(document, MarkdownDocument):
            return document.content

        if not isinstance(document, PDFDocument):
            raise DocumentTransformationError("Only Markdown and PDF lesson source documents are supported.")

        markdown_document, image_set = await self._pdf_to_markdown_transformer.execute(
            pdf_document=document
        )
        content = markdown_document.content

        if not image_set:
            logger.warning(
                no_images_log_event,
                document_url=document_url,
                log_type="technical"
            )
            return content

        for image in image_set:
            image_url = await self._cloud_manager.upload_document(document=image, user_id=user_id)
            content = content.replace(image.filename, image_url)

        return content


    async def lesson2_run(
        self, 
        user_id: str,
        lesson_id: str,
        document_url: str,
        subject: Subject,
        topic: Topic,
        concept: Concept
    ) -> Lesson2ExerciseExtractionResponse:
        """Main method to execute the exercise selection process based on the provided document URL."""

        try:
            if not document_url:
                content = "Document is empty. You can create exercises by yourself."
            else:
                content = await self._load_document_content(
                    user_id=user_id,
                    document_url=document_url,
                    no_images_log_event="create_lesson2.no_images_found",
                )

            lesson_creation_metadata = await self._lesson_manager.get_lesson_creation_metadata(
                lesson_id=lesson_id,
                user_id=user_id,
            )
            if lesson_creation_metadata is None:
                raise LessonManagerError("Lesson creation metadata was not found.")
            lesson1_artifact = await self._lesson_manager.get_lesson_artifact(
                exercise_id=lesson_creation_metadata.lesson1_exercise_id,
                user_id=user_id,
            )
            if lesson1_artifact is None:
                raise LessonManagerError("Lesson 1 artifact was not found.")
            if lesson1_artifact.lesson1 is None:
                raise LessonManagerError("Lesson 1 artifact is incomplete.")
            lesson1_summary = (
                getattr(lesson_creation_metadata, "lesson1_summary", None)
                or getattr(lesson_creation_metadata, "summary", None)
                or "No summary available."
            )

            # 3. Build a prompt for the chat service using the Markdown content then send it to the chat service.
            lesson2_exercise_extraction_input = {
                "content": content,
                "subject": subject,
                "topic": topic,
                "concept": concept,
                "lesson1_summary": lesson1_summary,
                "content_output_language": "Vietnamese",
            }
            extract_exercise_prompt = await self._prompt_builder.lesson2_exercise_extraction_prompt(**lesson2_exercise_extraction_input)
            llm_response = await self._llm_manager.generate_response(
                system_prompt=extract_exercise_prompt,
                messages=[],
                response_model=Exercise,
            )
            formatted_exercises = llm_response.content
            formatted_exercises.user_id = user_id
            exercise_id = lesson_id
            lesson2_summary = formatted_exercises.summary if formatted_exercises.summary else self._summarize_lesson2_exercise(formatted_exercises)
            lesson2_output = Lesson2ExerciseExtractionOutput(
                exercise=formatted_exercises,
                summary=lesson2_summary,
            )

            await self._lesson_manager.save_exercise(
                exercise_id=exercise_id,
                user_id=user_id,
                exercise=Lesson2StoredArtifact(
                    user_id=user_id,
                    lesson1=lesson1_artifact.lesson1,
                    lesson2=Lesson2StoredSection(
                        exercise=formatted_exercises,
                        summary=lesson2_summary,
                    ),
                    subject=lesson_creation_metadata.subject,
                    topic=lesson_creation_metadata.topic,
                    concept=lesson_creation_metadata.concept,
                ),
            ) 

            lesson_creation_metadata.lesson2_exercise_id = exercise_id
            lesson_creation_metadata.lesson2_summary = lesson2_summary
            await self._lesson_manager.save_lesson_creation_metadata(
                lesson_id=lesson_id,
                user_id=user_id,
                metadata=lesson_creation_metadata,
            )

            await self._lesson_manager.save_exercise(
                exercise_id=lesson_id,
                user_id=user_id,
                exercise=formatted_exercises
            )

            logger.info(
                "create_lesson2.completed",
                log_type="business",
                user_id=user_id,
                document_url=document_url,
            )

            return Lesson2ExerciseExtractionResponse(
                exercise_id=exercise_id,
                output=lesson2_output,
                usage=llm_response.usage,
            )
        
        except CloudManagerError as e:
            logger.error(
                "create_lesson2.cloud_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to fetch document from cloud storage.") from e
        
        except LLMManagerError as e:
            logger.error(
                "create_lesson2.llm_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to generate response from LLM manager.") from e
        
        except PromptGenerationError as e:
            logger.error(
                "create_lesson2.prompt_generation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to generate prompt for exercise extraction.") from e
        
        except ProfileManagerError as e:
            logger.error(
                "create_lesson2.profile_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to retrieve student profile for exercise selection.") from e
        
        except LessonManagerError as e:
            logger.error(
                "create_lesson2.lesson_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to save or retrieve exercises from the exercise manager.") from e
        
        except DocumentTransformationError as e:
            logger.error(
                "create_lesson2.document_transformation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to transform document to Markdown format.") from e
        
        except ProblemSelectionAnalysisError as e:
            logger.error(
                "create_lesson2.problem_selection_analysis_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to analyze problem for exercise selection.") from e
        
        except Exception as e:
            logger.error(
                "create_lesson2.unexpected.failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Unexpected error during lesson 2 creation process.") from e

    async def lesson1_run(
        self,
        user_id: str,
        lesson_id: str,
        document_url: str,
        previous_lessons: List[Concept],
        subject: Subject,
        topic: Topic,
        concept: Concept
    ):
        """Main method to create lesson 1 base on the provided document URL and user context."""
        try:
            if not document_url:
                content = "Document is empty. You can create content by yourself."
            else:
                content = await self._load_document_content(
                    user_id=user_id,
                    document_url=document_url,
                    no_images_log_event="create_lesson1.no_images_found",
                )

            lesson1_creation_input = {
                "content": content,
                "content_output_language": "Vietnamese",
                "subject": subject,
                "topic": topic,
                "concept": concept,
                "previous_lessons": previous_lessons
            }
            lesson1_creation_prompt = await self._prompt_builder.lesson1_document_extraction_prompt(**lesson1_creation_input)
            llm_response = await self._llm_manager.generate_response(
                system_prompt=lesson1_creation_prompt,
                messages=[],
                response_model=Lesson1CreationOutput
            )

            lesson1_creation_output = llm_response.content
            exercise_id = self._lesson1_exercise_id(lesson_id)

            await self._lesson_manager.save_exercise(
                exercise_id=exercise_id,
                user_id=user_id,
                exercise=Lesson1StoredArtifact(
                    user_id=user_id,
                    lesson1=Lesson1StoredSection(
                        learning_content=lesson1_creation_output.knowledge,
                        exercise=lesson1_creation_output.exercises,
                        summary=lesson1_creation_output.summary,
                    ),
                    subject=subject,
                    topic=topic,
                    concept=concept,
                ),
            )

            lesson_creation_metadata = CreateLessonMetadata(
                user_id=user_id,
                lesson_id=lesson_id,
                lesson1_exercise_id=exercise_id,
                lesson1_summary=lesson1_creation_output.summary,
                subject=subject,
                topic=topic,
                concept=concept,
            )
            await self._lesson_manager.save_lesson_creation_metadata(
                lesson_id=lesson_id,
                user_id=user_id,
                metadata=lesson_creation_metadata
            )

            usage = llm_response.usage
            logger.info(
                "create_lesson1.completed",
                log_type="business",
                user_id=user_id,
            )

            return Lesson1CreationResponse(
                exercise_id=exercise_id,
                output=lesson1_creation_output,
                usage=usage,
            )

        except CloudManagerError as e:
            logger.error(
                "create_lesson1.cloud_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to fetch document from cloud storage.") from e

        except LLMManagerError as e:
            logger.error(
                "create_lesson1.llm_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to generate response from LLM manager.") from e

        except PromptGenerationError as e:
            logger.error(
                "create_lesson1.prompt_generation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to generate prompt for lesson creation.") from e

        except LessonManagerError as e:
            logger.error(
                "create_lesson1.lesson_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to save lesson creation metadata.") from e

        except DocumentTransformationError as e:
            logger.error(
                "create_lesson1.document_transformation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to transform document to Markdown format.") from e

        except ProblemSelectionAnalysisError as e:
            logger.error(
                "create_lesson1.problem_selection_analysis_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Failed to analyze problem for lesson creation.") from e

        except Exception as e:
            logger.error(
                "create_lesson1.unexpected.failed",
                error=str(e),
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Unexpected error during lesson 1 creation process.") from e

