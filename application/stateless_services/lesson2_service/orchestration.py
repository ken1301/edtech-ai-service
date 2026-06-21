from typing import List, Optional, Tuple

from application.stateless_services.lesson2_service.layers.classify_layer import ClassifyLayer
from application.stateless_services.lesson2_service.layers.ground_layer import GroundLayer
from application.stateless_services.lesson2_service.full_pipeline import FullPipeline
from application.stateless_services.lesson2_service.fast_path_reply import FastPathReply
from application.stateless_services.lesson2_service.safety_divert import SafetyDivert

from domain.models.lesson2_models.classify import ClassifyInput, ClassifyOutput, Routing
from domain.models.lesson2_models.ground import GroundInput, GroundOutput
from domain.models.lesson2_models.meta import SessionMetadata, Lesson2Request
from domain.models.overall_models.message import Message
from domain.models.overall_models.response import TokenUsage

from domain.exceptions import Lesson2PipelineError, Lesson2OrchestrationError

from infrastructure.logging import logger

RECENT_MESSAGE_WINDOW = 6

class Lesson2Orchestration:
    """Routes a request to the right path (safety / fast-path / full pipeline) per overall.md §2.2.
    Submissions skip Classify and go straight to Ground; chat messages are classified first.
    All branching lives here in code (design rule #4), not in prompts."""

    def __init__(
        self,
        classify_layer: ClassifyLayer,
        ground_layer: GroundLayer,
        full_pipeline: FullPipeline,
        fast_path_reply: FastPathReply,
        safety_divert: SafetyDivert,
    ):
        self._classify_layer = classify_layer
        self._ground_layer = ground_layer
        self._full_pipeline = full_pipeline
        self._fast_path_reply = fast_path_reply
        self._safety_divert = safety_divert

    async def process(
        self,
        request: Lesson2Request,
        history_msg: List[Message],
        session_metadata: SessionMetadata,
    ) -> Tuple[str, SessionMetadata, List]:
        try:
            logger.debug(
                "lesson2.orchestration.process.called",
                log_type="debug",
                session_id=session_metadata.session_id,
            )

            all_token_usage: List = []

            if request.is_submission:
                classify_output = None
                ground_output, ground_usage = await self._ground_submission(request, session_metadata)
                if ground_usage is not None:
                    all_token_usage.append(ground_usage)
            else:
                classify_output, classify_usage = await self._classify_message(
                    request, session_metadata, history_msg
                )
                if classify_usage is not None:
                    all_token_usage.append(classify_usage)
                ground_output = None

            if classify_output and classify_output.routing == Routing.SAFETY_DIVERT:
                content, session_metadata, usage = await self._safety_divert.process(
                    request=request,
                    classify_output=classify_output,
                    session_metadata=session_metadata,
                    history_msg=history_msg,
                )
                return content, session_metadata, all_token_usage + usage

            if classify_output and classify_output.routing == Routing.FAST_PATH_REPLY:
                content, session_metadata, usage = await self._fast_path_reply.process(
                    request=request,
                    classify_output=classify_output,
                    session_metadata=session_metadata,
                    history_msg=history_msg,
                )
                return content, session_metadata, all_token_usage + usage

            content, session_metadata, usage = await self._full_pipeline.process(
                request=request,
                classify_output=classify_output,
                ground_output=ground_output,
                session_metadata=session_metadata,
                history_msg=history_msg,
            )
            return content, session_metadata, all_token_usage + usage

        except Lesson2PipelineError as e:
            raise Lesson2PipelineError("Failed to process message through pipeline.") from e

        except Exception as e:
            logger.error(
                "lesson2.orchestration.process.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2OrchestrationError("Failed to process message.") from e

    async def _ground_submission(
        self, request: Lesson2Request, session_metadata: SessionMetadata
    ) -> Tuple[Optional[GroundOutput], Optional[TokenUsage]]:
        """Build GroundInput from the current problem + the student's running reasoning (from
        metadata) and the result_status from NestJS, then run the Ground judge."""
        problem = _current_problem(session_metadata)
        if problem is None:
            return None, None

        ground_input = GroundInput(
            problem_question=problem.question,
            problem_final_answer=problem.final_answer,
            open_approach=problem.open_approach,
            approach_list=problem.approach_list,
            student_reasoning=_current_reasoning(session_metadata),
            student_submitted_answer=request.user_msg,
            result_status=request.submission_data.status,
        )
        layer_response = await self._ground_layer.execute(ground_input)
        return layer_response.output, layer_response.usage

    async def _classify_message(
        self,
        request: Lesson2Request,
        session_metadata: SessionMetadata,
        history_msg: List[Message],
    ) -> Tuple[ClassifyOutput, Optional[TokenUsage]]:
        """Build ClassifyInput from the message + recent history + current problem context."""
        classify_input = ClassifyInput(
            user_msg=request.user_msg,
            is_submission=request.is_submission,
            submission_data=request.submission_data,
            recent_messages=(history_msg or [])[-RECENT_MESSAGE_WINDOW:],
            current_problem_id=session_metadata.current_problem_id,
            problem_question=[p.question for p in session_metadata.problem_list],
        )
        layer_response = await self._classify_layer.execute(classify_input)
        return layer_response.output, layer_response.usage


def _current_problem(session_metadata: SessionMetadata):
    if not session_metadata.problem_list:
        return None
    pid = session_metadata.current_problem_id
    if pid is not None:
        for problem in session_metadata.problem_list:
            if problem.problem_id == pid:
                return problem
    return session_metadata.problem_list[0]


def _current_reasoning(session_metadata: SessionMetadata) -> str:
    pid = session_metadata.current_problem_id
    if pid is None:
        return ""
    state = session_metadata.problem_state.get(pid)
    if state is None or state.current_approach_id is None:
        return ""
    aid = state.current_approach_id
    if 0 <= aid < len(state.approach_list):
        return state.approach_list[aid].reasoning
    return ""
