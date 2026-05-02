from infrastructure.logging import logger

from domain.models.message import Message, Role
from domain.ports.session_store_port import SessionStorePort
from domain.ports.llm_port import LLMPort
from domain.models.response import ChatResponse

from application.services.session_manager import SessionManager


class SocraticChat:
    """Core chat use case — handles one user turn with optional context compression."""

    def __init__(
        self,
        llm: LLMPort,
        session_store: SessionStorePort,
        session_manager: SessionManager,
        compression_llm: LLMPort = None,
    ):
        self.llm = llm
        self.session_store = session_store
        self.session_manager = session_manager
        # compression_llm is a cheaper/faster model (e.g. Haiku or llama-3.1-8b)
        self.compression_llm = compression_llm or llm

    async def execute(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        corr_id: str,
        session_meta: dict,
    ) -> ChatResponse:
        # --- Context compression when turn count exceeds threshold ---
        if self.session_manager.needs_compression(session_meta):
            await self._compress_context(session_id, session_meta)
            # Reset turn counter after compression
            session_meta["turn_count"] = self.session_manager.MESSAGES_TO_KEEP
            await self.session_manager.save_metadata(session_id, session_meta)

        history = await self.session_store.get_history(session_id)

        user_msg = Message(role=Role.USER, content=user_message, correlation_id=corr_id)
        messages_to_send = history + [user_msg]

        llm_result = await self.llm.generate_response(
            system_prompt=system_prompt,
            messages=messages_to_send,
        )

        ai_msg = Message(role=Role.ASSISTANT, content=llm_result.content, correlation_id=corr_id)

        await self.session_store.save_message(session_id, user_msg)
        await self.session_store.save_message(session_id, ai_msg)

        logger.info(
            "AI_RESPONSE_GENERATED",
            tokens=llm_result.usage.total_tokens if llm_result.usage else None,
            model=llm_result.model_name,
            session_id=session_id,
            correlation_id=corr_id,
        )

        return ChatResponse(
            content=llm_result.content,
            usage=llm_result.usage.model_dump() if llm_result.usage else {},
            correlation_id=corr_id,
        )

    async def _compress_context(self, session_id: str, session_meta: dict) -> None:
        """Summarise old messages with a cheap model and replace history."""
        old_msgs, recent_msgs = await self.session_manager.get_messages_for_compression(session_id)
        if not old_msgs:
            return

        compression_prompt = await self._build_compression_prompt()
        summary_result = await self.compression_llm.generate_response(
            system_prompt=compression_prompt,
            messages=old_msgs,
        )

        await self.session_manager.replace_history_with_summary(
            session_id=session_id,
            summary_text=summary_result.content,
            recent_messages=recent_msgs,
        )

        logger.info(
            "CONTEXT_COMPRESSED",
            session_id=session_id,
            compressed=len(old_msgs),
            kept=len(recent_msgs),
        )

    @staticmethod
    async def _build_compression_prompt() -> str:
        return (
            "Bạn là trợ lý tóm tắt hội thoại giáo dục. "
            "Hãy tóm tắt các tin nhắn sau thành một đoạn văn ngắn gọn (tối đa 200 từ). "
            "Giữ lại: điểm kiến thức quan trọng, lỗi học sinh đã mắc, tiến trình học tập. "
            "Trả về bằng cùng ngôn ngữ với cuộc hội thoại. Không thêm tiêu đề hay gạch đầu dòng."
        )
