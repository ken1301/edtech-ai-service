from application.stateless_services.llm_manager import LLMManager
from application.services.exercise_manager import ExerciseManager
from application.stateless_services.prompt_builder import PromptBuilder
from application.services.cloud_manager import CloudManager
from application.services.profile_manager import ProfileManager

from application.stateless_services.docs_transform import PDFToMarkdownTransformer
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService

from domain.models.exercise import Exercise, ExerciseForPurpose

from domain.exceptions import (
    LLMManagerError,
    CloudManagerError,
    PromptGenerationError,
    ProfileManagerError,
    ExerciseManagerError,
    DocumentTransformationError,
    ProblemSelectionAnalysisError,
    ExerciseSelectionUseCaseError
)

from infrastructure.logging import logger

class ExerciseSelectionUseCase:
    """Use case responsible for selecting appropriate exercises based on the provided PDF document and user context."""

    def __init__(
        self,
        llm_manager: LLMManager,
        cloud_manager: CloudManager,
        prompt_builder: PromptBuilder,
        profile_manager: ProfileManager,
        exercise_manager: ExerciseManager,
        pdf_to_markdown_transformer: PDFToMarkdownTransformer,
        adaptive_learning_service: AdaptiveLearningService
    ):
        self._llm_manager = llm_manager
        self._cloud_manager = cloud_manager
        self._prompt_builder = prompt_builder
        self._profile_manager = profile_manager
        self._exercise_manager = exercise_manager
        self._pdf_to_markdown_transformer = pdf_to_markdown_transformer
        self._adaptive_learning_service = adaptive_learning_service

    async def run(
        self, 
        user_id: str,
        document_url: str
    ) -> ExerciseForPurpose:
        """Main method to execute the exercise selection process based on the provided PDF document URL."""

        try:
            # 1. Fetch the PDF document from cloud storage using the document URL
            pdf_document = await self._cloud_manager.fetch_pdf_document(document_url=document_url)

            # 2. Transform the PDF document into Markdown format, including handling of embedded images
            markdown_document, image_set = await self._pdf_to_markdown_transformer.execute(pdf_document=pdf_document)

            # 3. Upload extracted images to cloud storage and get their accessible URLs
            if not image_set:
                logger.warning(
                    "NO_IMAGES_FOUND",
                    document_url=document_url,
                    log_type="technical"
                )
            else:
                for image in image_set:
                    image_url = await self._cloud_manager.upload_image_document(image_document=image)

                    # Replace the local image reference in the Markdown content with the uploaded image URL
                    markdown_document.content = markdown_document.content.replace(image.filename, image_url)

            # 4. Build a prompt for the chat service using the transformed Markdown content then send it to the chat service
            extract_exercise_prompt = await self._prompt_builder.exercise_extraction_prompt()
            chat_response = await self._llm_manager.generate_response(
                system_prompt=extract_exercise_prompt,
                messages=[{"role": "user", "content": markdown_document.content}],
                response_model=Exercise
            )
            formatted_exercises = chat_response.content

            # 5. Save the extracted exercises to the exercise store
            for exercise in formatted_exercises:
                await self._exercise_manager.save_exercise(exercise=exercise)

            # 6. Use the adaptive learning service to select the most suitable exercise for the student 
            student_profile = await self._profile_manager.get_student_profile(user_id=user_id)
            selected_exercise = await self._adaptive_learning_service.problem_select(
                student_profile=student_profile,
                exercise=formatted_exercises
            )        

            logger.info(
                "exercise_selection_usecase.completed",
                log_type="business",
                user_id=user_id,
                document_url=document_url,
            )

            return selected_exercise
        
        except CloudManagerError as e:
            logger.error(
                "exercise_selection_usecase.cloud_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to fetch PDF document from cloud storage.") from e
        
        except LLMManagerError as e:
            logger.error(
                "exercise_selection_usecase.llm_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to generate response from LLM manager.") from e
        
        except PromptGenerationError as e:
            logger.error(
                "exercise_selection_usecase.prompt_generation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to generate prompt for exercise extraction.") from e
        
        except ProfileManagerError as e:
            logger.error(
                "exercise_selection_usecase.profile_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to retrieve student profile for exercise selection.") from e
        
        except ExerciseManagerError as e:
            logger.error(
                "exercise_selection_usecase.exercise_manager_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to save or retrieve exercises from the exercise manager.") from e
        
        except DocumentTransformationError as e:
            logger.error(
                "exercise_selection_usecase.document_transformation_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to transform PDF document to Markdown format.") from e
        
        except ProblemSelectionAnalysisError as e:
            logger.error(
                "exercise_selection_usecase.problem_selection_analysis_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Failed to analyze problem for exercise selection.") from e
        
        except Exception as e:
            logger.error(
                "exercise_selection_usecase.unexpected_failed",
                log_type="technical",
                user_id=user_id,
                document_url=document_url,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseSelectionUseCaseError("Unexpected error during exercise selection process.") from e

