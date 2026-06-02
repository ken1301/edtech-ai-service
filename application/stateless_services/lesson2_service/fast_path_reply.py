from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer
from application.stateless_services.lesson2_service.safety_divert import SafetyDivert

from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.metadata import SessionMetadata

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
        classify_output: ClassifyOutput,
        session_metadata: SessionMetadata
    ) -> str:
        pass