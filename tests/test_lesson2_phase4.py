import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from adapters.inbound.rest.auth import AuthenticatedUser
from adapters.inbound.rest.lesson2_router import select_exercises
from adapters.inbound.rest.schemas import ExerciseSelectionRequest
from application.stateless_services.adaptive_learning_service import AdaptiveLearningService
from domain.models.lesson2_models.classify import ClassifyOutput, EmotionalSignal, Routing, Intent
from domain.models.lesson2_models.decide import DecideInput, ResponseDirective, ToneArbiterOutput
from domain.models.lesson2_models.exercise import Approach, Exercise, ExercisePattern, Lesson2Exercises, Problem
from domain.models.lesson2_models.evaluate import AffectiveState, EvaluateInput, EvaluateOutput
from domain.models.lesson2_models.ground import GroundOutput, ApproachVerdict
from domain.models.lesson2_models.meta import ApproachState, Lesson2Request, PerProblemState, SessionMetadata, SubmissionRecord
from domain.models.lesson2_models.response import ResponseInput
from domain.models.lesson2_models.common import Phase, ProcessState, ResponseClass, SubmissionData
from domain.models.overall_models.common import BloomLevel, ConceptType, Constraint, ProblemRole, Representation
from domain.models.overall_models.curriculum import Concept, Subject, Topic


def _problem(problem_id: int, role: ProblemRole) -> Problem:
    return Problem(
        problem_id=problem_id,
        question=f"Problem {problem_id}",
        approach_list=[
            Approach(
                summary="Direct approach",
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
                max_attempts=2,
            )
        ],
        final_answer="42",
        open_approach=False,
        recommended_problem_role=role,
        max_approach_trial=1,
    )


def _exercise() -> Exercise:
    role_order = [
        ProblemRole.REINFORCEMENT,
        ProblemRole.CHALLENGE,
        ProblemRole.EXPLORATION,
        ProblemRole.EXTENSION,
    ]
    return Exercise(
        problem_list=[_problem(index + 1, role_order[index % len(role_order)]) for index in range(8)],
        subject=Subject.IT,
        topic=Topic.PROGRAMMING,
        concept=Concept.FUNCTIONS,
        user_id="user-1",
    )


def _selection_request() -> ExerciseSelectionRequest:
    return ExerciseSelectionRequest(
        correlation_id="corr-1",
        user_id="user-1",
        exercise_id="exercise-1",
    )


class _LessonManagerStub:
    async def get_public_exercise(self, exercise_id: str) -> Exercise:
        return _exercise()


class _ProfileManagerStub:
    async def get_student_profile(self, user_id: str):
        return object()


class _AdaptiveLearningServiceStub:
    async def problem_select(self, student_profile, exercise: Exercise) -> Lesson2Exercises:
        return Lesson2Exercises(
            problem_set={
                ProblemRole.EXTENSION: [_problem(4, ProblemRole.EXTENSION)],
                ProblemRole.EXPLORATION: [_problem(3, ProblemRole.EXPLORATION)],
                ProblemRole.CHALLENGE: [_problem(2, ProblemRole.CHALLENGE)],
                ProblemRole.REINFORCEMENT: [_problem(1, ProblemRole.REINFORCEMENT)],
            }
        )


class Lesson2Phase4Tests(unittest.IsolatedAsyncioTestCase):
    async def test_lesson2_request_rejects_blank_ids_and_message(self):
        with self.assertRaises(ValidationError):
            Lesson2Request(
                user_id="   ",
                session_id="session-1",
                correlation_id="corr-1",
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                user_msg="help",
                is_submission=False,
            )

        with self.assertRaises(ValidationError):
            Lesson2Request(
                user_id="user-1",
                session_id="session-1",
                correlation_id="corr-1",
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
                user_msg="   ",
                is_submission=False,
            )

    async def test_exercise_selection_request_rejects_blank_ids(self):
        with self.assertRaises(ValidationError):
            ExerciseSelectionRequest(
                exercise_id="   ",
                user_id="user-1",
                correlation_id="corr-1",
            )

    async def test_submission_data_accepts_spec_alias(self):
        submission = SubmissionData.model_validate(
            {
                "status": False,
                "is_progress_farming": [True, 3],
            }
        )

        self.assertEqual(submission.is_progress_farm, (True, 3))

    async def test_classify_output_rejects_out_of_range_scores(self):
        with self.assertRaises(ValidationError):
            ClassifyOutput(
                intent=Intent.LEARNING_DISCUSSION,
                intent_confidence=1.2,
                emotional=EmotionalSignal(
                    valence=0.5,
                    frustration=0.2,
                    confusion=0.1,
                    confidence_tone=0.7,
                ),
                learning_relevance=0.8,
                references_problem_id=1,
                abuse_flags=[],
                routing=Routing.FULL_PIPELINE,
            )

    async def test_evaluate_output_rejects_out_of_range_progress_signals(self):
        with self.assertRaises(ValidationError):
            EvaluateOutput(
                phase=Phase.PROBLEM,
                phase_confidence=0.8,
                current_approach_id=0,
                process_state=ProcessState.DISCOVERING,
                solution_proximity=1.5,
                stuck=False,
                approach_switched=False,
                student_reasoning_compressed="working",
                misconceptions=[],
                affect=AffectiveState(
                    frustration=0.2,
                    engagement=0.8,
                    confidence=0.6,
                ),
                summary="ok",
            )

    async def test_decide_input_rejects_out_of_range_progress(self):
        evaluate_output = EvaluateOutput(
            phase=Phase.PROBLEM,
            phase_confidence=0.8,
            current_approach_id=0,
            process_state=ProcessState.DISCOVERING,
            solution_proximity=0.5,
            stuck=False,
            approach_switched=False,
            student_reasoning_compressed="working",
            misconceptions=[],
            affect=AffectiveState(
                frustration=0.2,
                engagement=0.8,
                confidence=0.6,
            ),
            summary="ok",
        )

        with self.assertRaises(ValidationError):
            DecideInput(
                evaluate_output=evaluate_output,
                phase=Phase.PROBLEM,
                problem_index=0,
                total_problems=4,
                attempts_made=0,
                max_attempts=3,
                current_progress=101.0,
                abuse_flags=[],
            )

    async def test_evaluate_input_rejects_invalid_approach_semantics(self):
        with self.assertRaises(ValidationError):
            EvaluateInput(
                available_approaches=["Approach A"],
                current_approach_id=1,
                attempts_made=0,
                max_attempts=3,
            )

        with self.assertRaises(ValidationError):
            EvaluateInput(
                available_approaches=["Approach A"],
                current_approach_id=0,
                attempts_made=4,
                max_attempts=3,
            )

        with self.assertRaises(ValidationError):
            EvaluateInput(
                available_approaches=["Approach A"],
                is_submission=True,
                attempts_made=0,
                max_attempts=3,
            )

    async def test_decide_input_rejects_invalid_cross_field_semantics(self):
        evaluate_output = EvaluateOutput(
            phase=Phase.PROBLEM,
            phase_confidence=0.8,
            current_approach_id=0,
            process_state=ProcessState.DISCOVERING,
            solution_proximity=0.5,
            stuck=False,
            approach_switched=False,
            student_reasoning_compressed="working",
            misconceptions=[],
            affect=AffectiveState(
                frustration=0.2,
                engagement=0.8,
                confidence=0.6,
            ),
            summary="ok",
        )

        with self.assertRaises(ValidationError):
            DecideInput(
                evaluate_output=evaluate_output,
                phase=Phase.PROBLEM,
                problem_index=4,
                total_problems=4,
                attempts_made=0,
                max_attempts=3,
                current_progress=20.0,
                abuse_flags=[],
            )

        with self.assertRaises(ValidationError):
            DecideInput(
                evaluate_output=evaluate_output,
                is_submission=True,
                phase=Phase.PROBLEM,
                problem_index=0,
                total_problems=4,
                attempts_made=4,
                max_attempts=3,
                current_progress=20.0,
                abuse_flags=[],
            )

    async def test_response_input_rejects_invalid_cross_field_semantics(self):
        directive = ResponseDirective(
            response_class=ResponseClass.CONFIRM,
            tone_arbiter=ToneArbiterOutput(tone="peer", depth="short"),
        )

        with self.assertRaises(ValidationError):
            ResponseInput(
                response_directive=directive,
                problem_index=4,
                total_problems=4,
            )

        with self.assertRaises(ValidationError):
            ResponseInput(
                response_directive=directive,
                attempts_made=4,
                max_attempts=3,
            )

        with self.assertRaises(ValidationError):
            ResponseInput(
                response_directive=directive,
                is_submission=False,
                ground_verdict=ApproachVerdict.CORRECT,
            )

    async def test_per_problem_state_rejects_invalid_semantics(self):
        with self.assertRaises(ValidationError):
            PerProblemState(
                current_approach_id=1,
                approach_list=[
                    ApproachState(
                        reasoning="try",
                        attempts_made=0,
                        last_solution_proximity=0.2,
                        outcome="active",
                    )
                ],
            )

        with self.assertRaises(ValidationError):
            PerProblemState(
                current_approach_id=0,
                approach_list=[
                    ApproachState(
                        reasoning="try",
                        attempts_made=0,
                        last_solution_proximity=0.2,
                        outcome="active",
                    )
                ],
                approach_trial_count=0,
                submission_state=[
                    SubmissionRecord(
                        submitted_value="42",
                        result_status=False,
                        approach_verdict=ApproachVerdict.INCORRECT.value,
                        matched_approach_id=0,
                        matched_weakness=None,
                        farming_signal=(False, 0),
                    )
                ],
            )

    async def test_session_metadata_rejects_invalid_problem_links(self):
        with self.assertRaises(ValidationError):
            SessionMetadata(
                problem_list=[_problem(1, ProblemRole.REINFORCEMENT)],
                current_problem_id=2,
            )

        with self.assertRaises(ValidationError):
            SessionMetadata(
                problem_list=[_problem(1, ProblemRole.REINFORCEMENT)],
                problem_state={
                    2: PerProblemState(
                        current_approach_id=None,
                        approach_list=[],
                        approach_trial_count=0,
                    )
                },
            )

        with self.assertRaises(ValidationError):
            SessionMetadata(
                session_id="session-1",
                user_id="user-1",
                is_active=True,
                closed_at=datetime.now(timezone.utc),
            )

    async def test_session_metadata_rejects_runtime_problem_list_with_wrong_cardinality(self):
        with self.assertRaises(ValidationError):
            SessionMetadata(
                problem_list=[
                    _problem(1, ProblemRole.REINFORCEMENT),
                    _problem(2, ProblemRole.CHALLENGE),
                    _problem(3, ProblemRole.EXPLORATION),
                    _problem(4, ProblemRole.EXTENSION),
                    _problem(5, ProblemRole.EXTENSION),
                ]
            )

    async def test_session_metadata_rejects_runtime_problem_list_with_wrong_role_order(self):
        with self.assertRaises(ValidationError):
            SessionMetadata(
                problem_list=[
                    _problem(1, ProblemRole.CHALLENGE),
                    _problem(2, ProblemRole.REINFORCEMENT),
                    _problem(3, ProblemRole.EXPLORATION),
                    _problem(4, ProblemRole.EXTENSION),
                ]
            )

    async def test_ground_output_rejects_invalid_confidence(self):
        with self.assertRaises(ValidationError):
            GroundOutput(
                approach_verdict=ApproachVerdict.CORRECT,
                matched_approach_id=0,
                matched_weakness=None,
                judge_confidence=-0.1,
                explanation="clear",
            )

    async def test_exercise_requires_candidate_pool_role_coverage(self):
        with self.assertRaises(ValidationError):
            Exercise(
                problem_list=[_problem(index + 1, ProblemRole.REINFORCEMENT) for index in range(8)],
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
            )

    async def test_exercise_requires_candidate_pool_minimum_size(self):
        with self.assertRaises(ValidationError):
            Exercise(
                problem_list=[
                    _problem(1, ProblemRole.REINFORCEMENT),
                    _problem(2, ProblemRole.CHALLENGE),
                    _problem(3, ProblemRole.EXPLORATION),
                    _problem(4, ProblemRole.EXTENSION),
                ],
                subject=Subject.IT,
                topic=Topic.PROGRAMMING,
                concept=Concept.FUNCTIONS,
            )

    async def test_lesson2_exercises_normalizes_runtime_order(self):
        exercises = Lesson2Exercises(
            problem_set={
                ProblemRole.EXTENSION: [_problem(4, ProblemRole.EXTENSION)],
                ProblemRole.EXPLORATION: [_problem(3, ProblemRole.EXPLORATION)],
                ProblemRole.CHALLENGE: [_problem(2, ProblemRole.CHALLENGE)],
                ProblemRole.REINFORCEMENT: [_problem(1, ProblemRole.REINFORCEMENT)],
            }
        )

        self.assertEqual(
            [problem.problem_id for problem in exercises.ordered_problem_list()],
            [1, 2, 3, 4],
        )

    async def test_lesson2_exercises_rejects_role_mismatch(self):
        with self.assertRaises(ValidationError):
            Lesson2Exercises(
                problem_set={
                    ProblemRole.REINFORCEMENT: [_problem(1, ProblemRole.CHALLENGE)],
                    ProblemRole.CHALLENGE: [_problem(2, ProblemRole.CHALLENGE)],
                    ProblemRole.EXPLORATION: [_problem(3, ProblemRole.EXPLORATION)],
                    ProblemRole.EXTENSION: [_problem(4, ProblemRole.EXTENSION)],
                }
            )

    async def test_select_exercises_returns_runtime_problems_in_role_order(self):
        selected = await select_exercises(
            request=_selection_request(),
            authenticated_user=AuthenticatedUser(user_id="user-1"),
            lesson_manager=_LessonManagerStub(),
            profile_manager=_ProfileManagerStub(),
            adaptive_learning_service=_AdaptiveLearningServiceStub(),
        )

        self.assertEqual([problem.problem_id for problem in selected], [1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()