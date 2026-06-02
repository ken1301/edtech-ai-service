from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.lesson2_models.metadata import SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput

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
        classify_output: ClassifyOutput, 
        session_metadata: SessionMetadata
    ) -> str:
        pass