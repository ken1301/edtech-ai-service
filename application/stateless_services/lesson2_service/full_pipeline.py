from typing import List, Optional

from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.overall_models.message import Message
from domain.models.lesson2_models.evaluate import EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.decide import DecideInput
from domain.models.lesson2_models.meta import Lesson2Request, PerProblemState, SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.response import ResponseInput

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

RECENT_MESSAGE_WINDOW = 6
TOTAL_PROBLEMS = 4
DEFAULT_MAX_ATTEMPTS = 3

class FullPipeline:
    """Runs Evaluate -> Decide -> Respond -> StateWriter. Each builder derives its input from
    session_metadata (source of truth) plus the outputs of earlier layers this turn."""

    def __init__(
        self,
        evaluate_layer: EvaluateLayer,
        decide_layer: DecideLayer,
        response_layer: ResponseLayer,
        state_writer_layer: StateWriterLayer,
    ):
        self._evaluate_layer = evaluate_layer
        self._decide_layer = decide_layer
        self._response_layer = response_layer
        self._state_writer_layer = state_writer_layer

    async def process(
        self,
        request: Lesson2Request,
        classify_output: Optional[ClassifyOutput],
        ground_output: Optional[GroundOutput],
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]] = None,
    ) -> tuple[str, SessionMetadata, List]:
        try:
            logger.debug(
                "lesson2.full_pipeline.process.called",
                log_type="debug",
                session_id=session_metadata.session_id,
            )

            all_token_usage: List = []

            evaluate_input = self._build_evaluate_input(
                request, classify_output, ground_output, session_metadata, history_msg
            )
            evaluate_layer_response = await self._evaluate_layer.execute(evaluate_input)
            evaluate_output = evaluate_layer_response.output
            all_token_usage.append(evaluate_layer_response.usage)

            decide_input = self._build_decide_input(
                request, classify_output, ground_output, evaluate_output, session_metadata, history_msg
            )
            decide_layer_response = await self._decide_layer.execute(decide_input)
            decide_output = decide_layer_response.output
            all_token_usage.append(decide_layer_response.usage)

            response_input = self._build_response_input(
                request, classify_output, ground_output, evaluate_output, decide_output, session_metadata, history_msg
            )
            response_layer_response = await self._response_layer.execute(
                response_input, phase=evaluate_output.phase
            )
            all_token_usage.append(response_layer_response.usage)

            session_metadata = await self._state_writer_layer.execute(
                session_metadata=session_metadata,
                classify_output=classify_output,
                decide_output=decide_output,
                evaluate_output=evaluate_output,
                ground_output_if_submission=ground_output,
                request=request,
            )

            content = response_layer_response.output
            return (
                content if isinstance(content, str) else str(content),
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

    # --- input builders ----------------------------------------------------------

    @classmethod
    def _build_evaluate_input(
        cls,
        request: Lesson2Request,
        classify_output: Optional[ClassifyOutput],
        ground_output: Optional[GroundOutput],
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> EvaluateInput:
        problem = _current_problem(session_metadata)
        state = _current_state(session_metadata)
        return EvaluateInput(
            session_id=session_metadata.session_id,
            recent_messages=(history_msg or [])[-RECENT_MESSAGE_WINDOW:],
            problem_question=problem.question if problem else "",
            problem_role=problem.recommended_problem_role if problem else None,
            open_approach=problem.open_approach if problem else False,
            available_approaches=[a.summary for a in problem.approach_list] if problem else [],
            current_approach_id=state.current_approach_id if state else None,
            current_approach_reasoning=_current_reasoning(state),
            attempts_made=_attempts_made(state),
            max_attempts=_max_attempts(problem),
            is_submission=request.is_submission,
            ground_verdict=ground_output.approach_verdict if ground_output else None,
            matched_weakness=ground_output.matched_weakness if ground_output else None,
            phase_history=session_metadata.history_phase,
            last_evaluate_summary=session_metadata.last_evaluate_summary,
        )

    @classmethod
    def _build_decide_input(
        cls,
        request: Lesson2Request,
        classify_output: Optional[ClassifyOutput],
        ground_output: Optional[GroundOutput],
        evaluate_output: EvaluateOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> DecideInput:
        problem = _current_problem(session_metadata)
        state = _current_state(session_metadata)
        abuse = list(classify_output.abuse_flags) if classify_output else []
        return DecideInput(
            session_id=session_metadata.session_id,
            classify_output=classify_output,
            ground_output=ground_output,
            evaluate_output=evaluate_output,
            is_submission=request.is_submission,
            result_status=request.submission_data.status if request.is_submission else None,
            phase=evaluate_output.phase,
            problem_role=problem.recommended_problem_role if problem else None,
            problem_index=_problem_index(session_metadata),
            total_problems=len(session_metadata.problem_list) or TOTAL_PROBLEMS,
            attempts_made=_attempts_made(state),
            max_attempts=_max_attempts(problem),
            current_progress=session_metadata.current_progress,
            abuse_flags=abuse,
        )

    @classmethod
    def _build_response_input(
        cls,
        request: Lesson2Request,
        classify_output: Optional[ClassifyOutput],
        ground_output: Optional[GroundOutput],
        evaluate_output: EvaluateOutput,
        decide_output,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> ResponseInput:
        problem = _current_problem(session_metadata)
        state = _current_state(session_metadata)
        return ResponseInput(
            response_directive=decide_output.directive,
            phase=evaluate_output.phase,
            problem_question=problem.question if problem else "",
            problem_role=problem.recommended_problem_role if problem else None,
            problem_index=_problem_index(session_metadata),
            total_problems=len(session_metadata.problem_list) or TOTAL_PROBLEMS,
            current_progress=session_metadata.current_progress,
            evaluate_summary=evaluate_output.summary,
            affect=evaluate_output.affect,
            student_reasoning=evaluate_output.student_reasoning_compressed,
            process_state=evaluate_output.process_state,
            solution_proximity=evaluate_output.solution_proximity,
            stuck=evaluate_output.stuck,
            attempts_made=_attempts_made(state),
            max_attempts=_max_attempts(problem),
            is_submission=request.is_submission,
            ground_verdict=ground_output.approach_verdict if ground_output else None,
            matched_weakness=ground_output.matched_weakness if ground_output else None,
            classify=classify_output,
            recent_messages=(history_msg or [])[-RECENT_MESSAGE_WINDOW:],
        )


# --- shared metadata accessors ---------------------------------------------------

def _current_problem(session_metadata: SessionMetadata):
    if not session_metadata.problem_list:
        return None
    pid = session_metadata.current_problem_id
    if pid is not None:
        for problem in session_metadata.problem_list:
            if problem.problem_id == pid:
                return problem
    return session_metadata.problem_list[0]


def _current_state(session_metadata: SessionMetadata) -> Optional[PerProblemState]:
    pid = session_metadata.current_problem_id
    if pid is None:
        return None
    return session_metadata.problem_state.get(pid)


def _current_reasoning(state: Optional[PerProblemState]) -> str:
    if state is None or state.current_approach_id is None:
        return ""
    aid = state.current_approach_id
    if 0 <= aid < len(state.approach_list):
        return state.approach_list[aid].reasoning
    return ""


def _attempts_made(state: Optional[PerProblemState]) -> int:
    if state is None:
        return 0
    return state.approach_trial_count


def _problem_index(session_metadata: SessionMetadata) -> int:
    problem = _current_problem(session_metadata)
    if problem is None:
        return 0
    try:
        return session_metadata.problem_list.index(problem)
    except ValueError:
        return 0


def _max_attempts(problem) -> int:
    if problem is None:
        return DEFAULT_MAX_ATTEMPTS
    if problem.approach_list:
        return max((a.max_attempts for a in problem.approach_list), default=DEFAULT_MAX_ATTEMPTS)
    return DEFAULT_MAX_ATTEMPTS
