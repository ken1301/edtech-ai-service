from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from dependency_injector.wiring import inject, Provide

from infrastructure.container import Container

from application.use_cases.create_lesson_usecase import CreateLessonUseCase
from adapters.inbound.rest.auth import (
    AuthenticatedUser,
    enforce_authenticated_user_id,
    get_authenticated_user,
)
from adapters.inbound.rest.schemas import DocumentExtractionRequest, ExerciseExtractionRequest, ExerciseExtractionRequest

from domain.models.overall_models.response import Lesson2ExerciseExtractionResponse, Lesson1CreationResponse

from domain.exceptions import CreateLessonUseCaseError

from infrastructure.logging import logger

router = APIRouter()

@router.post("/lesson1", response_model=Lesson1CreationResponse)
@inject
async def extract_document(
    request: DocumentExtractionRequest,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    lesson_creation_manager: CreateLessonUseCase = Depends(Provide[Container.lesson_creation_manager]),
) -> Lesson1CreationResponse:
    try:
        user_id = enforce_authenticated_user_id(authenticated_user.user_id, request.user_id)
        response = await lesson_creation_manager.lesson1_run(
            user_id=user_id,
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

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document extraction: {str(e)}",
        )


@router.post("/lesson2", response_model=Lesson2ExerciseExtractionResponse)
@inject
async def extract_exercises(
    request: ExerciseExtractionRequest,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    lesson_creation_manager: CreateLessonUseCase = Depends(Provide[Container.lesson_creation_manager]),
) -> Lesson2ExerciseExtractionResponse:
    try:
        user_id = enforce_authenticated_user_id(authenticated_user.user_id, request.user_id)
        response = await lesson_creation_manager.lesson2_run(
            user_id=user_id,
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

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing exercise extraction: {str(e)}",
        )

    