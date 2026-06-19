from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from infrastructure.container import Container

from application.use_cases.chatbot_usecase import ChatbotUseCase
from application.stateless_services.learning_service import LearningService

from adapters.inbound.rest.schemas import ChatRequest, SyncAndCloseRequest

from domain.models.overall_models.response import Lesson2ChatResponse

from domain.exceptions import AuthorizationError, ChatBotUseCaseError

router = APIRouter()

@router.post("", response_model=Lesson2ChatResponse)
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

    