from typing import List, Optional

from application.stateless_services.lesson2_service.full_pipeline import FullPipeline
from application.stateless_services.lesson2_service.fast_path_reply import FastPathReply
from application.stateless_services.lesson2_service.safety_divert import SafetyDivert

from domain.models.lesson2_models.meta import SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput

from domain.models.overall_models.message import Message

class Orchestration:
    """Class responsible for orchestrating the overall flow of processing a user's message, including invoking the appropriate layers (e.g., classification, grounding, evaluation, decision-making, response generation, state writing) and handling any necessary branching or special cases (e.g., fast-path replies, safety diverting, etc.)."""

    def __init__(
        self, 
        full_pipeline: FullPipeline,
        fast_path_reply: FastPathReply,
        safety_divert: SafetyDivert
    ):
        self._full_pipeline = full_pipeline
        self._fast_path_reply = fast_path_reply
        self._safety_divert = safety_divert

    async def process(
        self, 
        user_msg: str,
        history_msg: List[Message],
        session_metadata: SessionMetadata
    ) -> str:
        pass

