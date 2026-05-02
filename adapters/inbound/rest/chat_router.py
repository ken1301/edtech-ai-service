from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from dependency_injector.wiring import inject, Provide

from adapters.inbound.rest.schemas import ChatRequest
from infrastructure.container import Container
from application.services.chatbot_manager import ChatbotManager
from domain.exceptions import SessionExpiredError
from domain.models.response import ChatResponse

router = APIRouter()


@router.post("/", response_model=ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chatbot_manager: ChatbotManager = Depends(Provide[Container.chatbot_manager]),
) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty",
        )

    try:
        response = await chatbot_manager.handle_chat(
            student_id=request.user_id,
            session_id=request.session_id,
            subject=request.subject,
            topic=request.topic,
            user_message=request.message,
            corr_id=request.corr_id,
            lang=request.lang,
            background_tasks=background_tasks,
        )
        return response

    except SessionExpiredError as e:
        raise HTTPException(status_code=440, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}",
        )
