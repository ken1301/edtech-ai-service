from application.stateless_services.prompt_builder import PromptBuilder
from application.stateless_services.llm_manager import LLMManager

from domain.models.lesson2_models.common import (
    ResponseClass,
    DisengagementLevel,
    DistressLevel,
    ProcessState,
    Lesson2LayerUsage,
)
from domain.models.lesson2_models.decide import (
    DecideInput,
    DecideOutput,
    ResponseDirective,
    ToneArbiterOutput,
)
from domain.models.lesson2_models.ground import ApproachVerdict
from domain.models.lesson2_models.classify import Intent

from domain.exceptions import Lesson2LayerError

from infrastructure.logging import logger


class DecideLayer:
    """Deterministic decision layer (overall.md §2.4 rule #4: branching in code, not prompts).

    Combines the 2-axis submission matrix (§2.3) with phase/attempt rules to pick a
    ResponseClass, then a small Tone Arbiter chooses tone/depth from perceived affect.
    No LLM call — pure rules over upstream layer outputs + session context.
    """

    def __init__(self, prompt_builder: PromptBuilder, llm_manager: LLMManager):
        self._prompt_builder = prompt_builder
        self._llm_manager = llm_manager

    async def execute(self, input: DecideInput) -> Lesson2LayerUsage:
        try:
            logger.debug("decide_layer.execute.called", log_type="debug", session_id=input.session_id)

            response_class, advance, intervene = self._select_response_directive(input)
            tone_arbiter_output = self._build_tone_arbiter_output(input, response_class)

            directive = ResponseDirective(
                response_class=response_class,
                tone_arbiter=tone_arbiter_output,
                advance=advance,
                intervene=intervene,
                rationale=f"verdict={getattr(input.ground_output, 'approach_verdict', None)} "
                          f"phase={input.phase} attempts={input.attempts_made}/{input.max_attempts}",
            )

            return Lesson2LayerUsage(output=DecideOutput(directive=directive), usage=None)

        except Exception as e:
            logger.error(
                "decide_layer.unexpected.failed",
                log_type="error",
                session_id=input.session_id,
                error=str(e),
                exc_info=True,
            )
            raise Lesson2LayerError("Failed to decide response.") from e

    @staticmethod
    def _select_response_directive(input: DecideInput):
        """Returns (response_class, advance, intervene)."""
        abuse = set(input.abuse_flags or [])
        classify = input.classify_output

        # --- Safety / abuse take precedence (also covers non-submission chat) ---
        if input.evaluate_output.affect.distress_level in (
            DistressLevel.GIVING_UP,
            DistressLevel.NON_ACADEMIC,
        ):
            return ResponseClass.SAFETY_HANDOFF, False, True
        if "jailbreak" in abuse or (classify and classify.intent == Intent.JAILBREAK_ATTEMPT):
            return ResponseClass.SAFETY_HANDOFF, False, True
        if "extract_answer" in abuse or (classify and classify.intent == Intent.ANSWER_EXTRACTION):
            return ResponseClass.REFUSE_ANSWER_REQ, False, False

        # --- Submission: 2-axis matrix (result_status × approach_verdict), §2.3 ---
        if input.is_submission and input.ground_output is not None:
            result_ok = input.result_status
            verdict = input.ground_output.approach_verdict

            # attempt limit reached on a wrong submission -> soft intervention (§1.5)
            attempts_exhausted = input.attempts_made >= input.max_attempts

            if verdict == ApproachVerdict.CORRECT and result_ok:
                # correct result via correct approach -> confirm + advance
                return ResponseClass.CONFIRM, True, False
            if result_ok and verdict in (ApproachVerdict.WEAK, ApproachVerdict.INCORRECT):
                # right answer, weak/odd approach -> confirm result but surface the weakness
                return ResponseClass.SURFACE_WEAKNESS, True, False
            if not result_ok and verdict == ApproachVerdict.CORRECT:
                # wrong answer but sound approach (slip) -> gentle probing
                if attempts_exhausted:
                    return ResponseClass.SOFT_INTERVENTION, False, True
                return ResponseClass.GUIDE_DISCOVERY, False, False
            if not result_ok:
                # wrong answer, wrong/weak approach -> peer counter-perspective
                if attempts_exhausted:
                    return ResponseClass.SOFT_INTERVENTION, False, True
                return ResponseClass.COUNTER_PERSPECTIVE, False, False
            # NOT_AN_ANSWER or anything else -> redirect to submit
            return ResponseClass.REDIRECT_TO_SUBMIT, False, False

        # --- Non-submission chat ---
        evaluate = input.evaluate_output

        if classify is not None:
            if classify.intent == Intent.META_QUERY:
                return ResponseClass.META_REPLY, False, False
            if classify.intent in (Intent.EMOTIONAL_EXPRESSION, Intent.GIVE_UP):
                return ResponseClass.EMPATHY, False, False

        # high frustration during discussion -> empathy first
        if evaluate.affect.frustration >= 0.7:
            return ResponseClass.EMPATHY, False, False

        # stuck and out of attempts mid-discussion -> soft intervention
        if evaluate.stuck and input.attempts_made >= input.max_attempts:
            return ResponseClass.SOFT_INTERVENTION, False, True

        # abandoning an approach that still had room (not yet at the attempt limit, and the
        # process wasn't actually failing) -> warn before the switch wastes the remaining tries.
        if (
            evaluate.approach_switched
            and input.attempts_made < input.max_attempts
            and evaluate.process_state not in (ProcessState.WRONG_STAGNANT, ProcessState.WRONG_DECLINING)
        ):
            return ResponseClass.APPROACH_SWITCH_WARNING, False, False

        # converged / very close on a non-submission turn -> redirect them to actually submit
        # (progress only moves on submission, §1.6) instead of endlessly discussing.
        if evaluate.process_state == ProcessState.CONVERGED or evaluate.solution_proximity >= 0.85:
            return ResponseClass.REDIRECT_TO_SUBMIT, False, False

        # default learning discussion -> probe the student's current step
        return ResponseClass.PROBE_INTERMEDIATE_PHASE, False, False

    @staticmethod
    def _build_tone_arbiter_output(input: DecideInput, response_class: ResponseClass) -> ToneArbiterOutput:
        affect = input.evaluate_output.affect

        # Tone: distress/empathy paths soften; firm only for abuse refusal.
        if response_class in (ResponseClass.SAFETY_HANDOFF, ResponseClass.EMPATHY):
            tone = "empathetic"
        elif response_class == ResponseClass.REFUSE_ANSWER_REQ:
            tone = "firm"
        elif affect.frustration >= 0.6 or affect.disengagement_level in (
            DisengagementLevel.DISENGAGING,
            DisengagementLevel.DISENGAGED,
        ):
            tone = "peer_soft"
        else:
            tone = "peer"

        # Depth: confirmations are terse, interventions/weakness-surfacing get more room.
        if response_class in (ResponseClass.CONFIRM, ResponseClass.REDIRECT_TO_SUBMIT, ResponseClass.META_REPLY):
            depth = "one_line"
        elif response_class in (
            ResponseClass.SOFT_INTERVENTION,
            ResponseClass.SURFACE_WEAKNESS,
            ResponseClass.COUNTER_PERSPECTIVE,
        ):
            depth = "medium"
        else:
            depth = "short"

        # Never reveal the final answer or skip steps unless explicitly soft-intervening.
        must_not_reveal = ["final_answer"]
        if response_class != ResponseClass.SOFT_INTERVENTION:
            must_not_reveal.append("next_step")

        return ToneArbiterOutput(tone=tone, depth=depth, must_not_reveal=must_not_reveal)
