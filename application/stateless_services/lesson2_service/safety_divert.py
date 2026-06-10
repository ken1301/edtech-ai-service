from typing import List, Optional

from application.stateless_services.lesson2_service.layers.response_layer import ResponseLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer

from domain.models.overall_models.common import ProblemRole, Role
from domain.models.lesson2_models.common import ResponseClass
from domain.models.lesson2_models.decide import ResponseDirective
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.response import ResponseInput
from domain.models.overall_models.message import Message

from domain.exceptions import Lesson2LayerError, Lesson2PipelineError

from infrastructure.logging import logger

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
        request: Lesson2Request,
        classify_output: ClassifyOutput, 
        session_metadata: SessionMetadata, 
        history_msg: Optional[List[Message]] = None,
    ) -> tuple[str, SessionMetadata, List]:
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
            )

            logger.info(
                "safety_divert.process.completed",
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
            raise Lesson2PipelineError("Failed to process safety divert.") from e

        except Exception as e:
            logger.error(
                "safety_divert.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2PipelineError("Failed to process safety divert.") from e

    @staticmethod
    def _build_response_input(
        request: Lesson2Request,
        classify_output: ClassifyOutput,
        session_metadata: SessionMetadata,
        history_msg: Optional[List[Message]],
    ) -> ResponseInput:
        pass


    #     recent_messages = list(history_msg or [])
    #     if user_msg:
    #         recent_messages = recent_messages + [Message(role=Role.USER, content=user_msg)]

    #     current_problem = self._current_problem(session_metadata)
    #     problem_role = current_problem.recommended_problem_role if current_problem else ProblemRole.REINFORCEMENT
    #     response_input = ResponseInput(
    #         problem_question=current_problem.question if current_problem else user_msg,
    #         problem_role=problem_role,
    #         response_directive=ResponseDirective(
    #             response_class=ResponseClass.SAFETY_HANDOFF,
    #             tone="empathetic",
    #             depth="short",
    #             must_not_reveal=["final_answer"],
    #         ),
    #         msg=user_msg,
    #         recent_messages=recent_messages,
    #         classify=classify_output,
    #         current_problem_index=self._current_problem_index(session_metadata, current_problem),
    #         is_submission=False,
    #     )

    #     response_usage = await self._response_layer.execute(response_input)
    #     await self._state_writer_layer.execute(
    #         session_metadata,
    #         response_directive=response_input.response_directive,
    #     )

    #     return response_usage.output if isinstance(response_usage.output, str) else str(response_usage.output)

    # @staticmethod
    # def _current_problem(session_metadata: SessionMetadata):
    #     if not session_metadata.problem_list:
    #         return None

    #     if session_metadata.current_problem_id is not None:
    #         for problem in session_metadata.problem_list:
    #             if problem.problem_id == session_metadata.current_problem_id:
    #                 return problem

    #     return session_metadata.problem_list[0]

    # @staticmethod
    # def _current_problem_index(session_metadata: SessionMetadata, current_problem) -> int:
    #     try:
    #         return session_metadata.problem_list.index(current_problem)
    #     except ValueError:
    #         return 0