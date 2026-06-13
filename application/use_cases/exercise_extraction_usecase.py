import asyncio
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from application.stateless_services.llm_manager import LLMManager
from application.services.exercise_manager import ExerciseManager
from application.stateless_services.prompt_builder import PromptBuilder
from application.services.cloud_manager import CloudManager
from application.services.profile_manager import ProfileManager

from application.stateless_services.docs_transform import PDFToMarkdownTransformer
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService

from domain.models.lesson2_models.exercise import Exercise, Lesson2Exercises
from domain.models.overall_models.document import ImageDocument, MarkdownDocument
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.response import ExerciseExtractionResponse

from domain.exceptions import (
    LLMManagerError,
    CloudManagerError,
    PromptGenerationError,
    ProfileManagerError,
    ExerciseManagerError,
    DocumentTransformationError,
    ProblemSelectionAnalysisError,
    ExerciseExtractionUseCaseError
)

from infrastructure.logging import logger

class ExerciseExtractionUseCase:
    """Use case responsible for selecting appropriate exercises based on the provided document and user context."""

    def __init__(
        self,
        llm_manager: LLMManager,
        cloud_manager: CloudManager,
        prompt_builder: PromptBuilder,
        pdf_to_markdown_transformer: PDFToMarkdownTransformer,
    ):
        self._llm_manager = llm_manager
        self._cloud_manager = cloud_manager
        self._prompt_builder = prompt_builder
        self._pdf_to_markdown_transformer = pdf_to_markdown_transformer

    async def run(
        self, 
        user_id: str,
        correlation_id: str,
        document_url: str,
        subject: Subject,
        topic: Topic,
        concept: Concept
    ) -> ExerciseExtractionResponse:
        """Main method to execute the exercise selection process based on the provided document URL."""

        try:
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
                    "NO_IMAGES_FOUND",
                    document_url=document_url,
                    log_type="technical"
                )
            else:
                for image in image_set:
                    image_url = await self._cloud_manager.upload_document(image_document=image)

                    # Replace the local image reference in the Markdown content with the uploaded image URL
                    markdown_document.content = markdown_document.content.replace(image.filename, image_url)

            # 3. Build a prompt for the chat service using the Markdown content then send it to the chat service.
            exercise_content = {
                "content": markdown_document.content,
                "subject": subject,
                "topic": topic,
                "concept": concept
            }
            extract_exercise_prompt = await self._prompt_builder.lesson2_exercise_extraction_prompt(**exercise_content)
            chat_response = await self._llm_manager.generate_response(
                system_prompt=extract_exercise_prompt,
                messages=[],
                response_model=Exercise
            )
            formatted_exercises = chat_response.content
            formatted_exercises.user_id = user_id

            logger.info(
                "exercise_extraction_usecase.completed",
                log_type="business",
                user_id=user_id,
                document_url=document_url,
            )

            return ExerciseExtractionResponse(
                output=formatted_exercises,
                usage=chat_response.usage,
                correlation_id=correlation_id
            )
        
        except CloudManagerError as e:
            logger.error(
                "exercise_extraction_usecase.cloud_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to fetch document from cloud storage.") from e
        
        except LLMManagerError as e:
            logger.error(
                "exercise_extraction_usecase.llm_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to generate response from LLM manager.") from e
        
        except PromptGenerationError as e:
            logger.error(
                "exercise_extraction_usecase.prompt_generation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to generate prompt for exercise extraction.") from e
        
        except ProfileManagerError as e:
            logger.error(
                "exercise_extraction_usecase.profile_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to retrieve student profile for exercise selection.") from e
        
        except ExerciseManagerError as e:
            logger.error(
                "exercise_extraction_usecase.exercise_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to save or retrieve exercises from the exercise manager.") from e
        
        except DocumentTransformationError as e:
            logger.error(
                "exercise_extraction_usecase.document_transformation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to transform document to Markdown format.") from e
        
        except ProblemSelectionAnalysisError as e:
            logger.error(
                "exercise_extraction_usecase.problem_selection_analysis_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Failed to analyze problem for exercise selection.") from e
        
        except Exception as e:
            logger.error(
                "exercise_extraction_usecase.unexpected_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseExtractionUseCaseError("Unexpected error during exercise selection process.") from e

