from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.decide import DecideOutput, ResponseDirective
from domain.models.lesson2_models.evaluate import EvaluateOutput
from domain.models.lesson2_models.ground import ApproachVerdict, GroundOutput
from domain.models.lesson2_models.meta import PerProblemState, SessionMetadata, SubmissionRecord

from domain.exceptions import Lesson2LayerError

from infrastructure.logging import logger

class StateWriterLayer:
    """Layer responsible for writing any necessary state back to the database or other storage mechanism, based on the output from the previous layers and any additional processing or rules that may be necessary."""

    def __init__(self):
        pass

    async def execute(
        self,
        session_metadata: SessionMetadata,
        classify_output: ClassifyOutput,
        decide_output: DecideOutput,
        evaluate_output: Optional[EvaluateOutput] = None,
        ground_output_if_submission: Optional[GroundOutput] = None,
    ) -> SessionMetadata:
        try: 
            logger.debug(
                "state_writer_layer.execute.called",
                log_type="debug",
                session_id=session_metadata.session_id,
            )
            pass

        except Exception as e:
            logger.error(
                "state_writer_layer.execute.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to write state.") from e
