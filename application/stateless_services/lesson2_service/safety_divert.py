from typing import List, Optional

from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.decide import ResponseDirective, ToneArbiterOutput
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.response import ResponseInput
from domain.models.overall_models.message import Message

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

class SafetyDivert:
    """Class responsible for monitoring the conversation for any potential safety issues (e.g., inappropriate content, harassment, etc.) and diverting the conversation to a safe response when necessary."""

    def __init__(
        self, 
        response_layer: ResponseLayer,
        state_writer_layer: StateWriterLayer
    ):
        self._response_layer = response_layer
        self._state_writer_layer = state_writer_layer

    async def process(
        self, 
        request: Lesson2Request,
        classify_output: ClassifyOutput, 
        session_metadata: SessionMetadata, 
        history_msg: Optional[List[Message]] = None,
    ) -> tuple[str, SessionMetadata, List]:
        try:
            all_token_usage = []

            response_input = self._build_response_input(
                request=request,
                classify_output=classify_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )
            response_layer_response = await self._response_layer.execute(response_input)
            all_token_usage.append(response_layer_response.usage)

            session_metadata = await self._state_writer_layer.execute(
                session_metadata=session_metadata,
                classify_output=classify_output,
                decide_output=None,
                evaluate_output=None,
                ground_output_if_submission=None,
                request=request,
            )   

            logger.info(
                "safety_divert.process.completed",
                log_type="business",
                session_id=session_metadata.session_id,
            )

            return (
                response_layer_response.output if isinstance(response_layer_response.output, str) else str(response_layer_response.output),
                session_metadata,
                all_token_usage,
            )


        except Lesson2LayerError as e:
            raise Lesson2PipelineError("Failed to process safety divert.") from e

        except Exception as e:
            logger.error(
                "safety_divert.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2PipelineError("Failed to process safety divert.") from e

    @staticmethod
    def _build_response_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> ResponseInput:
        directive = ResponseDirective(
            response_class=ResponseClass.SAFETY_HANDOFF,
            tone_arbiter=ToneArbiterOutput(
                tone="empathetic",
                depth="short",
                must_not_reveal=["final_answer"],
            ),
            intervene=True,
        )
        return ResponseInput(
            response_directive=directive,
            current_progress=session_metadata.current_progress,
            classify=classify_output,
            is_submission=request.is_submission,
            recent_messages=list(history_msg or []),
        )