import asyncio
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from application.services.cloud_manager import CloudManager
from application.services.lesson_manager import LessonManager

from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager
from application.stateless_services.docs_transform import PDFToMarkdownTransformer

from domain.models.lesson2_models.exercise import Exercise, Lesson2Exercises
from domain.models.overall_models.document import ImageDocument, MarkdownDocument
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.response import Lesson2ExerciseExtractionResponse
from domain.models.overall_models.lesson1 import Lesson1CreationOutput, Lesson1CreationResponse, CreateLessonMetadata

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

    async def lesson1_run(
        self,
        user_id: str,
        correlation_id: str,
        lesson_id: str,
        document_url: str,
        subject: Subject,
        topic: Topic,
        concept: Concept
    ):
        """Main method to create lesson 1 base on the provided document URL and user context."""
        try:
            if not document_url:
                content = "Document is empty. You can create content by yourself."
            else:
                document = await self._cloud_manager.fetch_document(document_url=document_url)
                if isinstance(document, MarkdownDocument):
                    markdown_document = document
                    image_set = []
                else: 
                    markdown_document, image_set = await self._pdf_to_markdown_transformer.execute(document=document)

                # 2. Upload extracted images to cloud storage and get their accessible URLs
                if not image_set:
                    logger.warning(
                        "create_lesson1.no_images_found",
                        document_url=document_url,
                        log_type="technical"
                    )
                else:
                    for image in image_set:
                        image_url = await self._cloud_manager.upload_document(image_document=image)

                        # Replace the local image reference in the Markdown content with the uploaded image URL
                        content = markdown_document.content.replace(image.filename, image_url)

            previous_lessons = []
            lesson1_creation_input = {
                "content": content,
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

            lesson_creation_metadata = CreateLessonMetadata(
                lesson_id=lesson_id,
                summary=lesson1_creation_output.summary
            )
            await self._lesson_manager.save_lesson_creation_metadata(
                lesson_id=lesson_id,
                metadata=lesson_creation_metadata
            )

            usage = llm_response.usage
            logger.info(
                "create_lesson1.completed",
                log_type="business",
                user_id=user_id,
            )

            return Lesson1CreationResponse(
                output=lesson1_creation_output,
                usage=usage,
                correlation_id=correlation_id
            )

        except Exception as e:
            logger.error(
                "create_lesson1.unexpected.failed",
                error=str(e),
                log_type="technical",
                exc_info=True,
            )
            raise CreateLessonUseCaseError("Unexpected error during lesson 1 creation process.") from e

    async def lesson2_run(
        self, 
        user_id: str,
        correlation_id: str,
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
                # 1. Load the document as Markdown, either by downloading it directly or converting from PDF.
                document = await self._cloud_manager.fetch_document(document_url=document_url)
                if isinstance(document, MarkdownDocument):
                    markdown_document = document
                    image_set = []
                else: 
                    markdown_document, image_set = await self._pdf_to_markdown_transformer.execute(document=document)

                # 2. Upload extracted images to cloud storage and get their accessible URLs
                if not image_set:
                    logger.warning(
                        "create_lesson2.no_images_found",
                        document_url=document_url,
                        log_type="technical"
                    )
                else:
                    for image in image_set:
                        image_url = await self._cloud_manager.upload_document(image_document=image)

                        # Replace the local image reference in the Markdown content with the uploaded image URL
                        content = markdown_document.content.replace(image.filename, image_url)

            lesson_creation_metadata = await self._lesson_manager.get_lesson_creation_metadata(lesson_id=lesson_id)
            lesson1_summary = lesson_creation_metadata.summary if lesson_creation_metadata else "No summary available."

            # 3. Build a prompt for the chat service using the Markdown content then send it to the chat service.
            lesson2_exercise_extraction_input = {
                "content": content,
                "subject": subject,
                "topic": topic,
                "concept": concept,
                "lesson1_summary": lesson1_summary
            }
            extract_exercise_prompt = await self._prompt_builder.lesson2_exercise_extraction_prompt(**lesson2_exercise_extraction_input)
            llm_response = await self._llm_manager.generate_response(
                system_prompt=extract_exercise_prompt,
                messages=[],
                response_model=Exercise
            )
            formatted_exercises = llm_response.content
            formatted_exercises.user_id = user_id

            logger.info(
                "create_lesson2.completed",
                log_type="business",
                user_id=user_id,
                document_url=document_url,
            )

            return Lesson2ExerciseExtractionResponse(
                output=formatted_exercises,
                usage=llm_response.usage,
                correlation_id=correlation_id
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

