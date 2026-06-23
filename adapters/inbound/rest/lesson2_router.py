from typing import List
import uuid

import structlog

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from domain.models.lesson2_models.exercise import Problem
from infrastructure.container import Container

from application.use_cases.chatbot_usecase import ChatbotUseCase

from application.services.lesson_manager import LessonManager
from application.services.profile_manager import ProfileManager
from application.stateless_services.learning_service import LearningService
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService

from adapters.inbound.rest.auth import (
    AuthenticatedUser,
    enforce_authenticated_user_id,
    get_authenticated_user,
)
from adapters.inbound.rest.schemas import ChatRequest, ExerciseSelectionRequest, SyncAndCloseRequest

from domain.models.overall_models.response import Lesson2ChatResponse, SyncAndCloseResponse

from domain.exceptions import (
    AuthorizationError,
    ChatBotUseCaseError,
    Lesson2SessionConflictError,
    Lesson2ValidationError,
    ProblemSelectionAnalysisError,
    LessonManagerError,
    ProfileManagerError,
    SessionClosedError,
    SessionClosingError,
    SessionNotFoundError,
    SyncAndCloseSessionError,
)

router = APIRouter()


def _current_correlation_id() -> str:
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    if isinstance(correlation_id, str) and correlation_id:
        return correlation_id
    return str(uuid.uuid4())

@router.post("/chat", response_model=Lesson2ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    chatbot_manager: ChatbotUseCase = Depends(Provide[Container.chatbot_manager]),
) -> Lesson2ChatResponse:
    try:
        user_id = enforce_authenticated_user_id(authenticated_user.user_id, request.user_id)
        response = await chatbot_manager.run(
            user_id=user_id,
            session_id=request.session_id,
            correlation_id=request.correlation_id,
            request=request,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept,
            background_task=background_tasks
        )

        return response

    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization failed for this session.",
        )

    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SessionClosedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Lesson2ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    except Lesson2SessionConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except ChatBotUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )

@router.post("/sync_and_close", response_model=SyncAndCloseResponse, status_code=status.HTTP_202_ACCEPTED)
@inject
async def sync_and_close(
    request: SyncAndCloseRequest,
    background_tasks: BackgroundTasks,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    learning_service: LearningService = Depends(Provide[Container.learning_service]),
) -> SyncAndCloseResponse:
    try:
        correlation_id = _current_correlation_id()
        user_id = enforce_authenticated_user_id(authenticated_user.user_id, request.user_id)
        metadata, newly_marked = await learning_service._session_manager.redis_mark_session_closing(
            session_id=request.session_id,
            user_id=user_id,
        )

        if metadata is None or not metadata.session_id or metadata.user_id != user_id:
            raise SessionNotFoundError("Session not found.")

        if metadata.closed_at is not None:
            return SyncAndCloseResponse(
                status="closed",
                detail="Session is already closed.",
            )

        already_marked = not newly_marked

        if newly_marked:
            background_tasks.add_task(
                learning_service.sync_and_close_session,
                user_id=user_id,
                session_id=request.session_id,
                correlation_id=correlation_id,
                subject=request.subject,
                topic=request.topic,
                concept=request.concept,
            )

        return SyncAndCloseResponse(
            status="closing" if already_marked else "accepted",
            detail="Session is already closing." if already_marked else "Session sync and close has been scheduled.",
        )

    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization failed for this session.",
        )

    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except SessionClosingError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except SyncAndCloseSessionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )

@router.post("/select-exercises", response_model=List[Problem])
@inject
async def select_exercises(
    request: ExerciseSelectionRequest,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
    lesson_manager: LessonManager = Depends(Provide[Container.lesson_manager]),
    profile_manager: ProfileManager = Depends(Provide[Container.profile_manager]),
    adaptive_learning_service: AdaptiveLearningService = Depends(Provide[Container.adaptive_learning_service]),
) -> List[Problem]:
    try:
        print("Received exercise selection request:", request)

        user_id = enforce_authenticated_user_id(authenticated_user.user_id, request.user_id)
        student_profile = await profile_manager.get_student_profile(
            user_id=user_id,
        )
        exercises = await lesson_manager.get_public_exercise(
            exercise_id=request.exercise_id,
        )

        selected_exercises = await adaptive_learning_service.problem_select(
            student_profile=student_profile,
            exercise=exercises,
        ) # -> Lesson2Exercises

        print("Selected exercises:", selected_exercises.ordered_problem_list())
        return selected_exercises.ordered_problem_list()
        
    except ProfileManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching student profile: {str(e)}",
        )

    except LessonManagerError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching exercises: {detail}",
        )

    except ProblemSelectionAnalysisError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing problem selection: {str(e)}",
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting exercises: {str(e)}",
        )
    
    