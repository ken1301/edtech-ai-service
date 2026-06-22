import unittest

from application.stateless_services.lesson2_service.layers.classify_layer import ClassifyLayer
from application.stateless_services.lesson2_service.layers.evaluate_layer import EvaluateLayer
from application.stateless_services.lesson2_service.layers.ground_layer import GroundLayer
from domain.exceptions import LLMManagerError, LLMManagerStructuredOutputError, Lesson2LayerError
from domain.models.lesson2_models.classify import ClassifyInput, Intent, Routing
from domain.models.lesson2_models.common import Phase, ProcessState
from domain.models.lesson2_models.evaluate import EvaluateInput
from domain.models.lesson2_models.exercise import Approach, ExercisePattern
from domain.models.lesson2_models.ground import GroundInput
from domain.models.overall_models.common import BloomLevel, ConceptType, Constraint, Representation
from domain.models.overall_models.common import Role
from domain.models.overall_models.message import Message


class _PromptBuilderStub:
    async def lesson2_classify_prompt(self, **context):
        return "classify prompt"

    async def lesson2_evaluate_prompt(self, **context):
        return "evaluate prompt"

    async def lesson2_ground_submission_prompt(self, **context):
        return "ground prompt"


class _LLMManagerStructuredFailureStub:
    async def generate_response(self, **kwargs):
        raise LLMManagerStructuredOutputError("structured output failed")


class _LLMManagerGeneralFailureStub:
    async def generate_response(self, **kwargs):
        raise LLMManagerError("general failure")


class Lesson2LayerFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_classify_layer_returns_safe_default_on_structured_output_failure(self):
        layer = ClassifyLayer(
            prompt_builder=_PromptBuilderStub(),
            llm_manager=_LLMManagerStructuredFailureStub(),
        )

        usage = await layer.execute(
            ClassifyInput(
                user_msg="Can you help me think through problem 2?",
                is_submission=False,
                recent_messages=[Message(role=Role.USER, content="hello")],
                current_problem_id=2,
                problem_question=["Problem one", "Problem two"],
            )
        )

        self.assertEqual(usage.output.intent, Intent.LEARNING_DISCUSSION)
        self.assertEqual(usage.output.routing, Routing.FULL_PIPELINE)
        self.assertEqual(usage.output.references_problem_id, 2)
        self.assertEqual(usage.usage, [])

    async def test_evaluate_layer_returns_safe_default_on_structured_output_failure(self):
        layer = EvaluateLayer(
            prompt_builder=_PromptBuilderStub(),
            llm_manager=_LLMManagerStructuredFailureStub(),
        )

        usage = await layer.execute(
            EvaluateInput(
                session_id="session-1",
                recent_messages=[Message(role=Role.USER, content="I think I should use substitution")],
                problem_question="Solve x + 2 = 4",
                available_approaches=["Substitute values"],
                current_approach_id=0,
                current_approach_reasoning="Try substitution",
                attempts_made=1,
                max_attempts=3,
                is_submission=False,
                phase_history=[Phase.PROBLEM],
            )
        )

        self.assertEqual(usage.output.phase, Phase.PROBLEM)
        self.assertEqual(usage.output.current_approach_id, 0)
        self.assertEqual(usage.output.process_state, ProcessState.DISCOVERING)
        self.assertEqual(usage.usage, [])

    async def test_classify_layer_still_raises_on_general_llm_failure(self):
        layer = ClassifyLayer(
            prompt_builder=_PromptBuilderStub(),
            llm_manager=_LLMManagerGeneralFailureStub(),
        )

        with self.assertRaises(Lesson2LayerError):
            await layer.execute(
                ClassifyInput(
                    user_msg="hello",
                    is_submission=False,
                    recent_messages=[],
                    current_problem_id=1,
                    problem_question=["Problem one"],
                )
            )

    async def test_ground_layer_does_not_degrade_on_structured_output_failure(self):
        layer = GroundLayer(
            prompt_builder=_PromptBuilderStub(),
            llm_manager=_LLMManagerStructuredFailureStub(),
        )

        with self.assertRaises(Lesson2LayerError):
            await layer.execute(
                GroundInput(
                    problem_question="What is 2 + 2?",
                    problem_final_answer="4",
                    open_approach=False,
                    approach_list=[
                        Approach(
                            summary="Direct addition",
                            bloom_level=BloomLevel.APPLY,
                            concept_type_used=[ConceptType.METHOD],
                            pattern=ExercisePattern(
                                cognitive_operation=[],
                                representation=[Representation.SYMBOLIC],
                                constraints=[Constraint.NONE],
                            ),
                            approach_answer="2 + 2 = 4",
                            strengths=[],
                            weaknesses=[],
                            max_attempts=1,
                        )
                    ],
                    student_reasoning="I added the two numbers.",
                    student_submitted_answer="4",
                    result_status=True,
                )
            )


if __name__ == "__main__":
    unittest.main()