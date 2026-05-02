import json
from typing import Optional

from infrastructure.logging import logger

from domain.ports.cache_port import CachePort
from domain.ports.db_port import MongoPort
from domain.ports.llm_port import LLMPort


class LearningService:

    def __init__(self, llm_gateway: LLMPort, db_gateway: MongoPort, cache_gateway: CachePort):
        self.llm = llm_gateway
        self.db = db_gateway
        self.cache = cache_gateway

    async def sync_and_close_session(self, summary_prompt: str, student_id: str, session_id: str, subject: str, topic: str = "General") -> None:
        history = await self.cache.get_history(session_id)

        if history:
            llm_result = await self.llm.generate_response(
                system_prompt=summary_prompt,
                messages=history,
            )

            try:
                data = json.loads(llm_result.content)
            except (ValueError, KeyError):
                data = {"score": 0.0, "misconceptions": []}

            await self.db.update_knowledge_map(
                student_id=student_id,
                subject=subject,
                topic=topic,
                data=data,
            )
        else:
            description = "EMPTY_HISTORY"


        logger.info(
            "UPDATE_STUDENT_PROFILE",
            student_id=student_id,
            session_id=session_id,
            description=description if description else ("SUCCESS" if llm_result.content else "EMPTY_RESPONSE"),
        )

        await self.cache.clear_session(session_id)
