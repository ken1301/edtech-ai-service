from typing import Dict, List, Optional

from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.classify import ClassifyOutput, Intent
from domain.models.lesson2_models.decide import ResponseDirective, ToneArbiterOutput
from domain.models.lesson2_models.meta import SessionMetadata, Lesson2Request
from domain.models.lesson2_models.response import ResponseInput
from domain.models.overall_models.message import Message

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

class FastPathReply:
    """Class responsible for generating a fast-path reply to the user, bypassing the more complex processing of the other layers when certain conditions are met (e.g., when the user's message is a simple greeting or farewell)."""

    def __init__(
        self, 
        response_layer: ResponseLayer,
        state_writer_layer: StateWriterLayer,
    ):
        self._response_layer = response_layer
        self._state_writer_layer = state_writer_layer

    async def process(
        self,
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]] = None,
    ) -> str:
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
                "fast_path_reply.process.completed",
                log_type="business",
                session_id=session_metadata.session_id,
            )

            return (
                response_layer_response.output if isinstance(response_layer_response.output, str) else str(response_layer_response.output),
                session_metadata,
                all_token_usage,
            )

        except Lesson2LayerError as e:
            raise Lesson2PipelineError("Failed to generate fast-path reply.") from e

        except Exception as e:
            logger.error(
                "fast_path_reply.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2PipelineError("Failed to generate fast-path reply.") from e

    @staticmethod
    def _build_response_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]] = None,
    ) -> ResponseInput:
        # Map the non-learning intent to a response class; all use the non-learning prompt.
        if classify_output.intent == Intent.META_QUERY:
            response_class = ResponseClass.META_REPLY
        elif classify_output.intent in (Intent.EMOTIONAL_EXPRESSION, Intent.GIVE_UP):
            response_class = ResponseClass.EMPATHY
        elif classify_output.intent == Intent.ANSWER_EXTRACTION:
            response_class = ResponseClass.REFUSE_ANSWER_REQ
        else:
            response_class = ResponseClass.META_REPLY

        directive = ResponseDirective(
            response_class=response_class,
            tone_arbiter=ToneArbiterOutput(
                tone="peer",
                depth="one_line",
                must_not_reveal=["final_answer"],
            ),
        )
        return ResponseInput(
            response_directive=directive,
            current_progress=session_metadata.current_progress,
            classify=classify_output,
            is_submission=request.is_submission,
            recent_messages=list(history_msg or []),
        )

    