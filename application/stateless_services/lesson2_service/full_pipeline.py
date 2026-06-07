from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.lesson2_models.meta import SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput

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
        classify_output: ClassifyOutput, 
        ground_output: GroundOutput, 
        session_metadata: SessionMetadata
    ) -> str:
        pass
