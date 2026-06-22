import unittest

from pydantic import ValidationError

from application.stateless_services.lesson2_service.layers.decide_layer import DecideLayer
from application.stateless_services.lesson2_service.layers.state_writer_layer import StateWriterLayer
from application.stateless_services.lesson2_service.orchestration import Lesson2Orchestration
from domain.exceptions import Lesson2SessionConflictError
from domain.models.lesson2_models.common import (
    DisengagementLevel,
    DistressLevel,
    Phase,
    ProcessState,
    ResponseClass,
    SubmissionData,
)
from domain.models.lesson2_models.decide import DecideOutput, ResponseDirective, ToneArbiterOutput
from domain.models.lesson2_models.decide import DecideInput
from domain.models.lesson2_models.evaluate import AffectiveState, EvaluateOutput
from domain.models.lesson2_models.exercise import Approach, ExercisePattern, Problem
from domain.models.lesson2_models.ground import ApproachVerdict, GroundOutput
from domain.models.lesson2_models.meta import Lesson2Request, SessionMetadata
from domain.models.overall_models.common import (
    BloomLevel,
    ConceptType,
    Constraint,
    ProblemRole,
    Representation,
)
from domain.models.overall_models.curriculum import Concept, Subject, Topic


class _GroundLayerStub:
    async def execute(self, input):
        raise AssertionError("ground layer should not be called in failing-path tests")


def _request(*, is_submission: bool, submission_data: SubmissionData | None = None) -> Lesson2Request:
    return Lesson2Request(
        user_id="user-1",
        session_id="session-1",
        correlation_id="corr-1",
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        user_msg="42",
        is_submission=is_submission,
        submission_data=submission_data,
    )


def _problem(problem_id: int = 101, role: ProblemRole = ProblemRole.REINFORCEMENT) -> Problem:
    return Problem(
        problem_id=problem_id,
        question="What is 6 * 7?",
        approach_list=[
            Approach(
                summary="Multiply directly",
                bloom_level=BloomLevel.APPLY,
                concept_type_used=[ConceptType.METHOD],
                pattern=ExercisePattern(
                    cognitive_operation=[],
                    representation=[Representation.SYMBOLIC],
                    constraints=[Constraint.NONE],
                ),
                approach_answer="42",
                strengths=[],
                weaknesses=[],
                max_attempts=3,
            )
        ],
        final_answer="42",
        open_approach=False,
        recommended_problem_role=role,
        max_approach_trial=3,
    )


def _evaluate_output() -> EvaluateOutput:
    return EvaluateOutput(
        phase=Phase.PROBLEM,
        phase_confidence=0.9,
        current_approach_id=0,
        process_state=ProcessState.DISCOVERING,
        solution_proximity=0.2,
        stuck=False,
        approach_switched=False,
        student_reasoning_compressed="working",
        misconceptions=[],
        affect=AffectiveState(
            frustration=0.1,
            engagement=0.9,
            confidence=0.5,
            disengagement_level=DisengagementLevel.ENGAGED,
            distress_level=DistressLevel.NONE,
        ),
        summary="ok",
    )


def _advance_decide_output() -> DecideOutput:
    return DecideOutput(
        directive=ResponseDirective(
            response_class=ResponseClass.WRAP_UP,
            tone_arbiter=ToneArbiterOutput(
                tone="peer",
                depth="short",
                must_not_reveal=[],
            ),
            advance=True,
            intervene=False,
            rationale="advance",
        )
    )


class Lesson2Phase1Tests(unittest.IsolatedAsyncioTestCase):
    async def test_non_submission_request_allows_missing_submission_data(self):
        request = _request(is_submission=False)
        self.assertIsNone(request.submission_data)

    async def test_submission_request_requires_submission_data(self):
        with self.assertRaises(ValidationError):
            _request(is_submission=True)

    async def test_ground_submission_requires_current_problem(self):
        orchestration = Lesson2Orchestration(
            classify_layer=None,
            ground_layer=_GroundLayerStub(),
            full_pipeline=None,
            fast_path_reply=None,
            safety_divert=None,
        )
        request = _request(
            is_submission=True,
            submission_data=SubmissionData(status=False, is_progress_farm=(False, 0)),
        )
        metadata = SessionMetadata(problem_list=[])

        with self.assertRaises(Lesson2SessionConflictError):
            await orchestration._ground_submission(request, metadata)

    async def test_state_writer_initializes_first_problem_for_submission(self):
        layer = StateWriterLayer()
        metadata = SessionMetadata(problem_list=[_problem()], current_problem_id=None)
        request = _request(
            is_submission=True,
            submission_data=SubmissionData(status=False, is_progress_farm=(True, 2)),
        )
        ground_output = GroundOutput(
            approach_verdict=ApproachVerdict.INCORRECT,
            matched_approach_id=0,
            matched_weakness="missed detail",
            judge_confidence=0.9,
            explanation="incorrect",
        )

        updated = await layer.execute(
            session_metadata=metadata,
            classify_output=None,
            decide_output=None,
            evaluate_output=None,
            ground_output_if_submission=ground_output,
            request=request,
        )

        self.assertEqual(updated.current_problem_id, 101)
        self.assertIn(101, updated.problem_state)
        self.assertEqual(updated.problem_state[101].submission_state[0].farming_signal, (True, 2))

    async def test_third_wrong_submission_triggers_soft_intervention(self):
        directive, advance, intervene = DecideLayer._select_response_directive(
            DecideInput(
                session_id="session-1",
                classify_output=None,
                ground_output=GroundOutput(
                    approach_verdict=ApproachVerdict.INCORRECT,
                    matched_approach_id=0,
                    matched_weakness="weak",
                    judge_confidence=0.8,
                    explanation="wrong",
                ),
                evaluate_output=_evaluate_output(),
                is_submission=True,
                result_status=False,
                phase=Phase.PROBLEM,
                problem_role=ProblemRole.REINFORCEMENT,
                problem_index=0,
                total_problems=4,
                attempts_made=2,
                max_attempts=3,
                current_progress=0.0,
                abuse_flags=[],
            )
        )

        self.assertEqual(directive, ResponseClass.SOFT_INTERVENTION)
        self.assertFalse(advance)
        self.assertTrue(intervene)

    async def test_successful_submission_marks_problem_solved_and_awards_progress(self):
        layer = StateWriterLayer()
        metadata = SessionMetadata(problem_list=[_problem()], current_problem_id=101)
        request = _request(
            is_submission=True,
            submission_data=SubmissionData(status=True, is_progress_farm=(False, 0)),
        )
        ground_output = GroundOutput(
            approach_verdict=ApproachVerdict.CORRECT,
            matched_approach_id=0,
            matched_weakness=None,
            judge_confidence=0.95,
            explanation="correct",
        )

        updated = await layer.execute(
            session_metadata=metadata,
            classify_output=None,
            decide_output=None,
            evaluate_output=_evaluate_output(),
            ground_output_if_submission=ground_output,
            request=request,
        )

        self.assertTrue(updated.problem_state[101].solved)
        self.assertEqual(updated.current_progress, StateWriterLayer.PROGRESS_BY_PROBLEM_INDEX[0])
        self.assertEqual(updated.problem_state[101].awarded_progress, StateWriterLayer.PROGRESS_BY_PROBLEM_INDEX[0])
        self.assertEqual(updated.problem_state[101].approach_trial_count, 1)
        self.assertEqual(updated.problem_state[101].approach_list[0].attempts_made, 1)

    async def test_farming_submission_pauses_progress_gain(self):
        layer = StateWriterLayer()
        metadata = SessionMetadata(problem_list=[_problem()], current_problem_id=101)
        request = _request(
            is_submission=True,
            submission_data=SubmissionData(status=False, is_progress_farm=(True, 3)),
        )
        ground_output = GroundOutput(
            approach_verdict=ApproachVerdict.INCORRECT,
            matched_approach_id=0,
            matched_weakness="guessing",
            judge_confidence=0.8,
            explanation="incorrect",
        )

        updated = await layer.execute(
            session_metadata=metadata,
            classify_output=None,
            decide_output=None,
            evaluate_output=_evaluate_output(),
            ground_output_if_submission=ground_output,
            request=request,
        )

        self.assertEqual(updated.current_progress, 0.0)
        self.assertEqual(updated.problem_state[101].awarded_progress, 0.0)
        self.assertEqual(updated.problem_state[101].submission_state[0].farming_signal, (True, 3))

    async def test_state_writer_advances_to_next_problem_when_directive_requests_it(self):
        layer = StateWriterLayer()
        metadata = SessionMetadata(
            problem_list=[
                _problem(101, ProblemRole.REINFORCEMENT),
                _problem(102, ProblemRole.CHALLENGE),
            ],
            current_problem_id=101,
        )

        updated = await layer.execute(
            session_metadata=metadata,
            classify_output=None,
            decide_output=_advance_decide_output(),
            evaluate_output=None,
            ground_output_if_submission=None,
            request=_request(is_submission=False),
        )

        self.assertEqual(updated.current_problem_id, 102)
        self.assertEqual(updated.phase_cycle_count, 1)


if __name__ == "__main__":
    unittest.main()