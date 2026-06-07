from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from adapters.inbound.rest.schemas import ChatRequest
from infrastructure.container import Container
from application.use_cases.chatbot_usecase import ChatbotUseCase
from domain.models.response import ChatResponse
from domain.exceptions import AuthorizationError, ChatBotUseCaseError

router = APIRouter()

@router.post("", response_model=ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chatbot_manager: ChatbotUseCase = Depends(Provide[Container.chatbot_manager]),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        response = await chatbot_manager.run(
            user_id=request.user_id,
            session_id=request.session_id,
            correlation_id=request.corr_id,
            student_message=request.message,
            subject=request.subject,
            background_task=background_tasks,
            topic=request.topic,
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

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )
