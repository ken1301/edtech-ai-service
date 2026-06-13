from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from application.stateless_services import adaptive_learning_service
from infrastructure.container import Container

from application.use_cases.exercise_extraction_usecase import ExerciseExtractionUseCase
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService
from application.services.exercise_manager import ExerciseManager
from application.services.profile_manager import ProfileManager

from adapters.inbound.rest.schemas import ExerciseExtractionRequest

from domain.models.overall_models.response import ExerciseExtractionResponse
from domain.models.lesson2_models.exercise import Problem

from domain.exceptions import ExerciseExtractionUseCaseError, ExerciseManagerError, ProfileManagerError, ProblemSelectionAnalysisError

from infrastructure.logging import logger

router = APIRouter()

@router.post("/extract", response_model=ExerciseExtractionResponse)
@inject
async def extract_exercises(
    request: ExerciseExtractionRequest,
    exercise_selection_manager: ExerciseExtractionUseCase = Depends(Provide[Container.exercise_extraction_manager]),
) -> ExerciseExtractionResponse:
    try:
        response = await exercise_selection_manager.run(
            user_id=request.user_id,
            correlation_id=request.corr_id,
            document_url=request.document_url,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept
        )

        return response

    except ExerciseExtractionUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing exercise extraction: {str(e)}",
        )

@router.post("/select", response_model=List[Problem])
@inject
async def select_exercises(
    exercise_id: str,
    user_id: str,
    exercise_manager: ExerciseManager = Depends(Provide[Container.exercise_manager]),
    profile_manager: ProfileManager = Depends(Provide[Container.profile_manager]),
    adaptive_learning_service: AdaptiveLearningService = Depends(Provide[Container.adaptive_learning_service]),
) -> List[Problem]:
    try:
        student_profile = await profile_manager.get_student_profile(user_id=user_id)
        exercise = await exercise_manager.get_exercise(exercise_id=exercise_id, user_id=user_id)

        selected_problems = await adaptive_learning_service.problem_select(
            exercise=exercise,
            student_profile=student_profile
        )

        response = []
        for _, problem_list in selected_problems.problem_set:
            response.append(problem_list[0])  # For simplicity, we return the first problem of each role. This can be adjusted as needed.

        return response

    except (ExerciseManagerError, ProfileManagerError, ProblemSelectionAnalysisError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting exercises: {str(e)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting exercises: {str(e)}",
        )
    