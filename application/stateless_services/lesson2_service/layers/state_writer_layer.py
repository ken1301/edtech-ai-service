from __future__ import annotations

from typing import Optional

from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.decide import DecideOutput
from domain.models.lesson2_models.evaluate import EvaluateOutput
from domain.models.lesson2_models.ground import ApproachVerdict, GroundOutput
from domain.models.lesson2_models.meta import (
    ApproachState,
    EmotionalState,
    Misconception,
    PerProblemState,
    SessionMetadata,
    SubmissionRecord,
    Lesson2Request,
)

from domain.exceptions import Lesson2LayerError

from infrastructure.logging import logger


class StateWriterLayer:
    """Deterministic state mutation (overall.md §2.4 rule #2: only this layer/orchestrator mutates
    SessionMetadata). Folds the turn's layer outputs back into metadata so it stays the single
    source of truth, and computes the progress delta on submission (Task 5)."""

    # Progress hyperparameters (4 problems -> 100%). Tunable.
    PROGRESS_PER_PROBLEM = 25.0   # cap each problem can contribute
    CORRECT_OPTIMAL = 25.0        # right answer via a correct/strong approach
    CORRECT_WEAK = 18.0           # right answer via a weak/odd approach
    INCORRECT = 8.0               # wrong answer but a genuine attempt ("Done > Perfect")
    FARMING = 0.0                 # detected farming -> progress paused (§1.6)
    MAX_PROGRESS = 100.0

    def __init__(self):
        pass

    async def execute(
        self,
        session_metadata: SessionMetadata,
        classify_output: Optional[ClassifyOutput],
        decide_output: Optional[DecideOutput],
        evaluate_output: Optional[EvaluateOutput] = None,
        ground_output_if_submission: Optional[GroundOutput] = None,
        request: Optional[Lesson2Request] = None,
    ) -> SessionMetadata:
        try:
            logger.debug(
                "state_writer_layer.execute.called",
                log_type="debug",
                session_id=session_metadata.session_id,
            )

            problem_state = self._ensure_problem_state(session_metadata)

            if evaluate_output is not None:
                self._apply_evaluate(session_metadata, problem_state, evaluate_output)

            is_submission = bool(request and request.is_submission and ground_output_if_submission is not None)
            if is_submission:
                self._apply_submission(
                    session_metadata, problem_state, request, ground_output_if_submission, evaluate_output
                )

            if decide_output is not None and decide_output.directive.advance:
                self._advance_problem(session_metadata)

            return session_metadata

        except Exception as e:
            logger.error(
                "state_writer_layer.execute.unexpected.failed",
                log_type="error",
                session_id=session_metadata.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to write state.") from e

    # --- helpers -----------------------------------------------------------------

    @staticmethod
    def _ensure_problem_state(session_metadata: SessionMetadata) -> Optional[PerProblemState]:
        pid = session_metadata.current_problem_id
        if pid is None:
            return None
        state = session_metadata.problem_state.get(pid)
        if state is None:
            state = PerProblemState()
            session_metadata.problem_state[pid] = state
        return state

    @staticmethod
    def _apply_evaluate(
        session_metadata: SessionMetadata,
        problem_state: Optional[PerProblemState],
        evaluate_output: EvaluateOutput,
    ) -> None:
        # Affect history
        session_metadata.last_evaluate_summary = evaluate_output.summary

        # Append this turn's perceived affect to the session emotion trajectory. Previously this
        # list was declared but never written, so the affect history was silently lost.
        affect = evaluate_output.affect
        if affect is not None:
            session_metadata.emotion_history.append(
                EmotionalState(
                    frustration=affect.frustration,
                    engagement=affect.engagement,
                    confidence=affect.confidence,
                    disengagement_level=affect.disengagement_level.value,
                    distress_level=affect.distress_level.value,
                )
            )

        # Misconceptions: merge perceived signals into the session list (dedup by description).
        existing = {m.description for m in session_metadata.misconception_list}
        for m in evaluate_output.misconceptions:
            if m.description not in existing:
                session_metadata.misconception_list.append(
                    Misconception(misconception_type=m.misconception_type, description=m.description)
                )
                existing.add(m.description)

        # Phase history
        session_metadata.history_phase.append(evaluate_output.phase)

        if problem_state is None:
            return

        problem_state.phase_history.append(evaluate_output.phase)

        # If the student moved to a different approach, record the switch on the one they left
        # (only if it wasn't already resolved) so the approach trajectory is auditable.
        prev_id = problem_state.current_approach_id
        new_id = evaluate_output.current_approach_id
        if (
            evaluate_output.approach_switched
            and prev_id is not None
            and prev_id != new_id
            and 0 <= prev_id < len(problem_state.approach_list)
        ):
            left = problem_state.approach_list[prev_id]
            if left.outcome == "active":
                # Submitted at least once on this approach before leaving -> forced switch;
                # otherwise the student chose to pivot on their own.
                left.outcome = "switched_after_limit" if left.attempts_made > 0 else "switched_voluntarily"

        problem_state.current_approach_id = new_id

        # Write the compressed running reasoning back onto the active approach so downstream
        # layers (e.g. Ground) read it from metadata next turn (spec Task 4 pattern).
        approach_idx = evaluate_output.current_approach_id
        if approach_idx is not None:
            while len(problem_state.approach_list) <= approach_idx:
                problem_state.approach_list.append(
                    ApproachState(
                        reasoning="",
                        attempts_made=0,
                        last_solution_proximity=0.0,
                        outcome="active",
                    )
                )
            active = problem_state.approach_list[approach_idx]
            active.reasoning = evaluate_output.student_reasoning_compressed or active.reasoning
            active.last_solution_proximity = evaluate_output.solution_proximity
            active.process_state = evaluate_output.process_state.value

    def _apply_submission(
        self,
        session_metadata: SessionMetadata,
        problem_state: Optional[PerProblemState],
        request: Lesson2Request,
        ground_output: GroundOutput,
        evaluate_output: Optional[EvaluateOutput],
    ) -> None:
        if problem_state is None:
            return

        result_status = request.submission_data.status
        is_farming, _ = request.submission_data.is_process_farm
        verdict = ground_output.approach_verdict

        problem_state.submission_state.append(
            SubmissionRecord(
                submitted_value=request.user_msg,
                result_status=result_status,
                approach_verdict=verdict.value,
                matched_approach_id=ground_output.matched_approach_id,
                matched_weakness=ground_output.matched_weakness,
                farming_signal=request.submission_data.is_process_farm,
            )
        )
        problem_state.approach_trial_count += 1
        if problem_state.current_approach_id is not None and problem_state.current_approach_id < len(problem_state.approach_list):
            problem_state.approach_list[problem_state.current_approach_id].attempts_made += 1

        delta = self._progress_delta(result_status, verdict, is_farming)
        self._credit_progress(session_metadata, problem_state, delta)

        if result_status:
            problem_state.solved = True

    def _progress_delta(self, result_status: bool, verdict: ApproachVerdict, is_farming: bool) -> float:
        """Only submissions move the bar; correct > incorrect but both > 0; farming pauses it (§1.6)."""
        if is_farming:
            return self.FARMING
        if verdict == ApproachVerdict.NOT_AN_ANSWER:
            return 0.0
        if result_status:
            return self.CORRECT_OPTIMAL if verdict == ApproachVerdict.CORRECT else self.CORRECT_WEAK
        return self.INCORRECT

    def _credit_progress(
        self,
        session_metadata: SessionMetadata,
        problem_state: PerProblemState,
        delta: float,
    ) -> None:
        if delta <= 0:
            return
        # Cap per-problem contribution, then cap session total.
        room = self.PROGRESS_PER_PROBLEM - problem_state.awarded_progress
        granted = max(0.0, min(delta, room))
        if granted <= 0:
            return
        problem_state.awarded_progress += granted
        session_metadata.current_progress = min(
            self.MAX_PROGRESS, session_metadata.current_progress + granted
        )

    @staticmethod
    def _advance_problem(session_metadata: SessionMetadata) -> None:
        problems = session_metadata.problem_list
        if not problems:
            return
        ids = [p.problem_id for p in problems]
        current = session_metadata.current_problem_id
        if current is None:
            session_metadata.current_problem_id = ids[0]
            return
        if current in ids:
            i = ids.index(current)
            if i + 1 < len(ids):
                session_metadata.current_problem_id = ids[i + 1]
                session_metadata.phase_cycle_count += 1
