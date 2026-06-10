from typing import List, Optional, Tuple
import re

from application.stateless_services.lesson2_service.layers.classify_layer import ClassifyLayer
from application.stateless_services.lesson2_service.layers.ground_layer import GroundLayer
from application.stateless_services.lesson2_service.full_pipeline import FullPipeline
from application.stateless_services.lesson2_service.fast_path_reply import FastPathReply
from application.stateless_services.lesson2_service.safety_divert import SafetyDivert

from domain.models.lesson2_models.classify import ClassifyOutput, EmotionalSignal, Intent, Routing
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.meta import SessionMetadata, Lesson2Request
from domain.models.lesson2_models.response import Lesson2LayerUsage
from domain.models.overall_models.message import Message
from domain.models.overall_models.response import TokenUsage

from domain.exceptions import Lesson2PipelineError, Lesson2OrchestrationError

from infrastructure.logging import logger

class Lesson2Orchestration:
    """Class responsible for orchestrating the overall flow of processing a user's message, including invoking the appropriate layers (e.g., classification, grounding, evaluation, decision-making, response generation, state writing) and handling any necessary branching or special cases (e.g., fast-path replies, safety diverting, etc.)."""

    def __init__(
        self, 
        classify_layer: ClassifyLayer,
        ground_layer: GroundLayer,
        full_pipeline: FullPipeline,
        fast_path_reply: FastPathReply,
        safety_divert: SafetyDivert
    ):  
        self._classify_layer = classify_layer
        self._ground_layer = ground_layer
        self._full_pipeline = full_pipeline
        self._fast_path_reply = fast_path_reply
        self._safety_divert = safety_divert

    async def process(
        self, 
        request: Lesson2Request,
        history_msg: List[Message],
        session_metadata: SessionMetadata
    ) -> str:
        try:
            all_token_usage = []

            classify_output, classify_usage = await self._classify_message(request, session_metadata)
            all_token_usage.append(classify_usage)
            if request.is_submission: 
                ground_output, ground_usage = await self._ground_submission(request, session_metadata)
                all_token_usage.append(ground_usage)
            else:
                ground_output = None

            if classify_output.routing == Routing.SAFETY_DIVERT:
                return await self._safety_divert.process(
                    request=request,
                    classify_output=classify_output,
                    session_metadata=session_metadata,
                    history_msg=history_msg,
                )

            if classify_output.routing == Routing.FAST_PATH_REPLY:
                return await self._fast_path_reply.process(
                    request=request,
                    classify_output=classify_output,
                    session_metadata=session_metadata,
                    history_msg=history_msg,
                )

            return await self._full_pipeline.process(
                request=request,
                classify_output=classify_output,
                ground_output=ground_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )

        except Lesson2PipelineError as e:
            raise Lesson2PipelineError("Failed to process message through pipeline.") from e

        except Exception as e:
            logger.error(
                "lesson2.orchestration.process.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2OrchestrationError("Failed to process message.") from e

    def _ground_submission(self, request: Lesson2Request, session_metadata: SessionMetadata) -> Tuple[Optional[GroundOutput], TokenUsage]:
        """Placeholder grounding logic for submissions - in a real implementation, this would likely involve invoking an LLM or other complex logic to determine the correctness of the submission and generate appropriate feedback"""
        pass

    def _classify_message(self, request: Lesson2Request, session_metadata: SessionMetadata) -> Tuple[ClassifyOutput, TokenUsage]:
        """Placeholder classification logic - in a real implementation, this would likely involve invoking an LLM or other complex logic to analyze the user's message and determine their intent, emotional state, etc."""
        pass

    

