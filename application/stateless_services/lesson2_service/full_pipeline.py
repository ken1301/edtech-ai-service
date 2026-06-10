from typing import List, Optional

from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.overall_models.common import ProblemRole, Role
from domain.models.overall_models.message import Message
from domain.models.lesson2_models.common import Phase, ResponseClass
from domain.models.lesson2_models.decide import DecideInput, ResponseDirective
from domain.models.lesson2_models.evaluate import (
    ApproachHistoryEntry,
    EvaluateInput,
    EvaluateOutput,
    ProblemSnapshot,
)
from domain.models.lesson2_models.exercise import Problem
from domain.models.lesson2_models.meta import Lesson2Request, PerProblemState, SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import ApproachVerdict, GroundOutput
from domain.models.lesson2_models.response import ResponseInput

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

class FullPipeline:
    """Class responsible for orchestrating the full pipeline of layers for processing a user's message and generating an appropriate response, including classification, grounding, evaluation, decision-making, response generation, and state writing."""

    def __init__(
        self, 
        evaluate_layer: EvaluateLayer,
        decide_layer: DecideLayer,
        response_layer: ResponseLayer,
        state_writer_layer: StateWriterLayer
    ):
        self._evaluate_layer = evaluate_layer
        self._decide_layer = decide_layer
        self._response_layer = response_layer
        self._state_writer_layer = state_writer_layer

    async def process(
        self, 
        request: Lesson2Request,
        classify_output: ClassifyOutput, 
        ground_output: Optional[GroundOutput], 
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]] = None,
    ) -> tuple[str, SessionMetadata, List]:
        try:
            all_token_usage = []

            evaluate_input = self._build_evaluate_input(
                request=request,
                classify_output=classify_output,
                ground_output=ground_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )
            evaluate_layer_response = await self._evaluate_layer.execute(evaluate_input)
            evaluate_output = evaluate_layer_response.output
            all_token_usage.append(evaluate_layer_response.usage)

            decide_input = self._build_decide_input(
                request=request,
                classify_output=classify_output,
                ground_output=ground_output,  
                evaluate_output=evaluate_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )
            decide_layer_response = await self._decide_layer.execute(decide_input)
            decide_output = decide_layer_response.output
            all_token_usage.append(decide_layer_response.usage)

            response_input = self._build_response_input(
                request=request,
                classify_output=classify_output,
                ground_output=ground_output,
                evaluate_output=evaluate_output,
                decide_output=decide_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )
            response_layer_response = await self._response_layer.execute(response_input, phase=evaluate_output.phase)
            all_token_usage.append(response_layer_response.usage)

            session_metadata = await self._state_writer_layer.execute(
                session_metadata=session_metadata,
                classify_output=classify_output,
                decide_output=decide_output,
                evaluate_output=evaluate_output,
                ground_output_if_submission=ground_output,                
            )

            logger.info(
                "full_pipeline.process.completed",
                log_type="info",
                session_id=session_metadata.session_id,
                token_usage=all_token_usage,
            )

            return (
                response_layer_response.output if isinstance(response_layer_response.output, str) else str(response_layer_response.output),
                session_metadata,
                all_token_usage,
            )

        except Lesson2LayerError as e:
            raise Lesson2PipelineError("Failed to process full pipeline.") from e

        except Exception as e:
            logger.error(
                "full_pipeline.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2PipelineError("Failed to process full pipeline.") from e

    @staticmethod
    def _build_evaluate_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        ground_output: Optional[GroundOutput],
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> EvaluateInput:
        pass

    @staticmethod
    def _build_decide_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        ground_output: Optional[GroundOutput],
        evaluate_output: EvaluateOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> DecideInput:
        pass

    @staticmethod
    def _build_response_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        ground_output: Optional[GroundOutput],
        evaluate_output: EvaluateOutput,
        decide_output: DecideInput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> ResponseInput:
        pass

