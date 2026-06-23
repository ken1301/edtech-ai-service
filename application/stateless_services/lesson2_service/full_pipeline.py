from typing import List, Optional

from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.overall_models.message import Message
from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.evaluate import EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.decide import DecideInput, ResponseDirective, ToneArbiterOutput
from domain.models.lesson2_models.meta import Lesson2Request, PerProblemState, SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.response import ResponseInput

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

RECENT_MESSAGE_WINDOW = 10
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
            all_token_usage: List = []

            evaluate_input = self._build_evaluate_input(
                request, classify_output, ground_output, session_metadata, history_msg
            )
            evaluate_layer_response = await self._evaluate_layer.execute(evaluate_input)
            evaluate_output = evaluate_layer_response.output
            all_token_usage.append(evaluate_layer_response.usage)

            # print(f"Evaluate Output: {evaluate_output}")

            decide_input = self._build_decide_input(
                request, classify_output, ground_output, evaluate_output, session_metadata, history_msg
            )
            decide_layer_response = await self._decide_layer.execute(decide_input)
            decide_output = decide_layer_response.output
            all_token_usage.append(decide_layer_response.usage)

            # print(f"Decide Output: {decide_output}")

            session_metadata = await self._state_writer_layer.execute(
                session_metadata=session_metadata,
                classify_output=classify_output,
                decide_output=decide_output,
                evaluate_output=evaluate_output,
                ground_output_if_submission=ground_output,
                request=request,
            )

            response_input = self._build_response_input(
                request, classify_output, ground_output, evaluate_output, decide_output, session_metadata, history_msg
            )
            response_layer_response = await self._response_layer.execute(
                response_input, phase=evaluate_output.phase
            )
            all_token_usage.append(response_layer_response.usage)

            content = response_layer_response.output

            logger.info(
                "full_pipeline.process.completed",
                log_type="business",
                session_id=session_metadata.session_id,
            )

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

    async def process_wrap_up(
        self,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]] = None,
    ) -> tuple[str, Optional[object]]:
        try:
            response_input = self._build_wrap_up_response_input(session_metadata, history_msg)
            response_layer_response = await self._response_layer.execute(response_input)
            content = response_layer_response.output
            return (
                content if isinstance(content, str) else str(content),
                response_layer_response.usage,
            )

        except Lesson2LayerError as e:
            raise Lesson2PipelineError("Failed to generate wrap-up response.") from e

        except Exception as e:
            logger.error(
                "full_pipeline.wrap_up.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2PipelineError("Failed to generate wrap-up response.") from e

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
        attempt_approach_id, attempts_made, max_attempts = _attempt_context(problem, state, ground_output)
        return EvaluateInput(
            session_id=session_metadata.session_id,
            recent_messages=(history_msg or [])[-RECENT_MESSAGE_WINDOW:],
            problem_question=problem.question if problem else "",
            problem_role=problem.recommended_problem_role if problem else None,
            open_approach=problem.open_approach if problem else False,
            available_approaches=[a.summary for a in problem.approach_list] if problem else [],
            current_approach_id=attempt_approach_id,
            current_approach_reasoning=_current_reasoning(state, attempt_approach_id),
            attempts_made=attempts_made,
            max_attempts=max_attempts,
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
        _, attempts_made, max_attempts = _attempt_context(problem, state, ground_output)
        abuse = list(classify_output.abuse_flags) if classify_output else []
        return DecideInput(
            session_id=session_metadata.session_id,
            classify_output=classify_output,
            ground_output=ground_output,
            evaluate_output=evaluate_output,
            is_submission=request.is_submission,
            result_status=ground_output.result_verdict if request.is_submission and ground_output else None,
            phase=evaluate_output.phase,
            problem_role=problem.recommended_problem_role if problem else None,
            problem_index=_problem_index(session_metadata),
            total_problems=len(session_metadata.problem_list) or TOTAL_PROBLEMS,
            attempts_made=attempts_made,
            max_attempts=max_attempts,
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
        _, attempts_made, max_attempts = _attempt_context(problem, state, ground_output)
        return ResponseInput(
            response_directive=decide_output.directive,
            subject=request.subject.value,
            topic=request.topic.value,
            concept=request.concept.value,
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
            attempts_made=attempts_made,
            max_attempts=max_attempts,
            is_submission=request.is_submission,
            ground_verdict=ground_output.approach_verdict if ground_output else None,
            matched_weakness=ground_output.matched_weakness if ground_output else None,
            classify=classify_output,
            recent_messages=(history_msg or [])[-RECENT_MESSAGE_WINDOW:],
        )

    @classmethod
    def _build_wrap_up_response_input(
        cls,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> ResponseInput:
        problem = _current_problem(session_metadata)
        directive = ResponseDirective(
            response_class=ResponseClass.WRAP_UP,
            tone_arbiter=ToneArbiterOutput(
                tone="peer",
                depth="short",
                must_not_reveal=["final_answer"],
            ),
        )
        return ResponseInput(
            response_directive=directive,
            problem_question=problem.question if problem else "",
            problem_role=problem.recommended_problem_role if problem else None,
            problem_index=_problem_index(session_metadata),
            total_problems=len(session_metadata.problem_list) or TOTAL_PROBLEMS,
            current_progress=session_metadata.current_progress,
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


def _attempt_approach_id(
    state: Optional[PerProblemState],
    ground_output: Optional[GroundOutput] = None,
) -> Optional[int]:
    if state is not None and state.current_approach_id is not None:
        return state.current_approach_id
    if ground_output is not None:
        return ground_output.matched_approach_id
    return None


def _attempt_context(problem, state: Optional[PerProblemState], ground_output: Optional[GroundOutput] = None) -> tuple[Optional[int], int, int]:
    approach_id = _attempt_approach_id(state, ground_output)
    max_attempts = _max_attempts(problem, approach_id)
    attempts_made = min(_attempts_made(state, approach_id), max_attempts)
    return approach_id, attempts_made, max_attempts


def _current_reasoning(state: Optional[PerProblemState], approach_id: Optional[int] = None) -> str:
    if state is None:
        return ""
    aid = state.current_approach_id if approach_id is None else approach_id
    if aid is None:
        return ""
    if 0 <= aid < len(state.approach_list):
        return state.approach_list[aid].reasoning
    return ""


def _attempts_made(state: Optional[PerProblemState], approach_id: Optional[int] = None) -> int:
    if state is None:
        return 0
    aid = state.current_approach_id if approach_id is None else approach_id
    if aid is None:
        return state.approach_trial_count
    if aid is not None and 0 <= aid < len(state.approach_list):
        return state.approach_list[aid].attempts_made
    return state.approach_trial_count


def _problem_index(session_metadata: SessionMetadata) -> int:
    problem = _current_problem(session_metadata)
    if problem is None:
        return 0
    try:
        return session_metadata.problem_list.index(problem)
    except ValueError:
        return 0


def _max_attempts(problem, approach_id: Optional[int] = None) -> int:
    if problem is None:
        return DEFAULT_MAX_ATTEMPTS
    aid = approach_id
    if aid is not None and 0 <= aid < len(problem.approach_list):
        return problem.approach_list[aid].max_attempts
    if problem.approach_list:
        return max((a.max_attempts for a in problem.approach_list), default=DEFAULT_MAX_ATTEMPTS)
    return DEFAULT_MAX_ATTEMPTS
