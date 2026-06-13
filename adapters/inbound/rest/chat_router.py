from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from infrastructure.container import Container
from application.use_cases.chatbot_usecase import ChatbotUseCase

from adapters.inbound.rest.schemas import ChatRequest

from domain.models.overall_models.response import ChatResponse

from domain.exceptions import AuthorizationError, ChatBotUseCaseError

router = APIRouter()

@router.post("", response_model=ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chatbot_manager: ChatbotUseCase = Depends(Provide[Container.chatbot_manager]),
) -> ChatResponse:
    try:
        response = await chatbot_manager.run(
            user_id=request.user_id,
            session_id=request.session_id,
            correlation_id=request.corr_id,
            request=request,
            subject=request.subject,
            topic=request.topic,
            concept=request.concept,
            background_tasks=background_tasks
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