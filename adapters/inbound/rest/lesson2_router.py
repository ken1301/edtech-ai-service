from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from domain.models.lesson2_models.exercise import Problem
from infrastructure.container import Container

from application.use_cases.chatbot_usecase import ChatbotUseCase

from application.services.lesson_manager import LessonManager
from application.services.profile_manager import ProfileManager
from application.stateless_services.learning_service import LearningService
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService

from adapters.inbound.rest.schemas import ChatRequest, ExerciseSelectionRequest, SyncAndCloseRequest

from domain.models.overall_models.response import Lesson2ChatResponse

from domain.exceptions import AuthorizationError, ChatBotUseCaseError, ProblemSelectionAnalysisError, LessonManagerError, ProfileManagerError

router = APIRouter()

@router.post("/chat", response_model=Lesson2ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chatbot_manager: ChatbotUseCase = Depends(Provide[Container.chatbot_manager]),
) -> Lesson2ChatResponse:
    try:
        response = await chatbot_manager.run(
            user_id=request.user_id,
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

    except ChatBotUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )

@router.post("/sync_and_close", response_model=Lesson2ChatResponse)
@inject
async def sync_and_close(
    request: SyncAndCloseRequest,
    background_tasks: BackgroundTasks,
    learning_service: LearningService = Depends(Provide[Container.learning_service]),
) -> None:
    try:
        background_tasks.add_task(
            learning_service.sync_and_close_session,
            user_id=request.user_id,
            session_id=request.session_id,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept,
        )

    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authorization failed for this session.",
        )

    except ChatBotUseCaseError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )

@router.post("/select-exercises", response_model=List[Problem])
async def select_exercises(
    request: ExerciseSelectionRequest,
    lesson_manager: LessonManager = Depends(Provide[Container.lesson_manager]),
    profile_manager: ProfileManager = Depends(Provide[Container.profile_manager]),
    adaptive_learning_service: AdaptiveLearningService = Depends(Provide[Container.adaptive_learning_service]),
) -> List[Problem]:
    try:
        student_profile = await profile_manager.get_student_profile(
            user_id=request.user_id,
        )
        exercises = await lesson_manager.get_exercise(
            exercise_id=request.exercise_id,
            user_id=request.user_id,
        )

        selected_exercises = await adaptive_learning_service.problem_select(
            student_profile=student_profile,
            exercise=exercises,
        ) # -> Lesson2Exercises

        # class Lesson2Exercises(BaseModel):
        #     problem_set: Dict[ProblemRole, List[Problem]]

        problem_list = []
        for role, problems in selected_exercises.problem_set.items():
            problem_list.append(problems[0])  # Select the first problem for each role

        return problem_list
        
    except ProfileManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching student profile: {str(e)}",
        )

    except LessonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching exercises: {str(e)}",
        )

    except ProblemSelectionAnalysisError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing problem selection: {str(e)}",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error selecting exercises: {str(e)}",
        )
    
    