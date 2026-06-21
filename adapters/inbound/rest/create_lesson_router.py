from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from application.stateless_services import adaptive_learning_service
from infrastructure.container import Container

from application.use_cases.create_lesson_usecase import CreateLessonUseCase
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService
from application.services.lesson_manager import LessonManager
from application.services.profile_manager import ProfileManager

from adapters.inbound.rest.schemas import DocumentExtractionRequest, ExerciseExtractionRequest, ExerciseExtractionRequest

from domain.models.overall_models.response import Lesson2ExerciseExtractionResponse
from domain.models.overall_models.lesson1 import Lesson1CreationResponse
from domain.models.lesson2_models.exercise import Problem

from domain.exceptions import CreateLessonUseCaseError

from infrastructure.logging import logger

router = APIRouter()

@router.post("/lesson1", response_model=Lesson1CreationResponse)
@inject
async def extract_document(
    request: DocumentExtractionRequest,
    lesson_creation_manager: CreateLessonUseCase = Depends(Provide[Container.lesson_creation_manager]),
) -> Lesson1CreationResponse:
    try:
        response = await lesson_creation_manager.lesson1_run(
            user_id=request.user_id,
            correlation_id=request.correlation_id,
            document_url=request.document_url,
            lesson_id=request.lesson_id,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept
        )

        return response

    except CreateLessonUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document extraction: {str(e)}",
        )



@router.post("/lesson2", response_model=Lesson2ExerciseExtractionResponse)
@inject
async def extract_exercises(
    request: ExerciseExtractionRequest,
    lesson_creation_manager: CreateLessonUseCase = Depends(Provide[Container.lesson_creation_manager]),
) -> Lesson2ExerciseExtractionResponse:
    try:
        response = await lesson_creation_manager.lesson2_run(
            user_id=request.user_id,
            correlation_id=request.correlation_id,
            document_url=request.document_url,
            lesson_id=request.lesson_id,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept
        )

        return response

    except CreateLessonUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing exercise extraction: {str(e)}",
        )

    