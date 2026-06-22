from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.evaluate import AffectiveState, EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.common import (
    DisengagementLevel,
    DistressLevel,
    Lesson2LayerUsage,
    Phase,
    ProcessState,
)

from domain.exceptions import Lesson2LayerError, LLMManagerError, LLMManagerStructuredOutputError

from infrastructure.logging import logger

class EvaluateLayer:
    """Layer responsible for evaluating the output from the previous layers and determining the appropriate response based on the content and context of the message, as well as any additional processing or rules that may be necessary."""

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    @staticmethod
    def _safe_default_output(input: EvaluateInput) -> EvaluateOutput:
        preserved_approach_id = input.current_approach_id
        if preserved_approach_id is not None and preserved_approach_id >= len(input.available_approaches):
            preserved_approach_id = None

        return EvaluateOutput(
            phase=Phase.PROBLEM,
            phase_confidence=0.2,
            current_approach_id=preserved_approach_id,
            process_state=ProcessState.DISCOVERING,
            solution_proximity=0.0,
            stuck=False,
            approach_switched=False,
            student_reasoning_compressed=input.current_approach_reasoning or "Fallback evaluation: unavailable structured analysis.",
            misconceptions=[],
            affect=AffectiveState(
                frustration=0.3,
                engagement=0.5,
                confidence=0.4,
                disengagement_level=DisengagementLevel.COASTING,
                distress_level=DistressLevel.NONE,
            ),
            summary="Fallback evaluation used because structured analysis was unavailable.",
        )

    async def execute(self, input: EvaluateInput) -> Lesson2LayerUsage:
        try:
            logger.debug(
                "evaluate_layer.called",
                log_type="debug",
            )
            
            prompt = await self._prompt_builder.lesson2_evaluate_prompt(**input.model_dump())
            llm_response = await self._llm_manager.generate_response(
                system_prompt=prompt,
                messages=input.recent_messages,
                response_model=EvaluateOutput,
            )

            return Lesson2LayerUsage(output=llm_response.content, usage=llm_response.usage)

        except LLMManagerStructuredOutputError as e:
            logger.warning(
                "evaluate_layer.structured_output_degraded",
                log_type="technical",
                session_id=input.session_id,
                error=str(e),
            )
            return Lesson2LayerUsage(output=self._safe_default_output(input), usage=[])

        except LLMManagerError as e:
            raise Lesson2LayerError("LLM Manager failed to generate evaluation.") from e

        except Exception as e:
            logger.error(
                "evaluate_layer.unexpected.failed",
                log_type="error",
                session_id=input.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to evaluate user message.") from e