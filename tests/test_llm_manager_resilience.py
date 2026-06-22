import asyncio
import unittest
from unittest.mock import patch

from pydantic import BaseModel

from application.stateless_services.llm_manager import LLMManager
from domain.exceptions import (
    LLMAdapterError,
    LLMConfigurationError,
    LLMManagerAuthenticationError,
    LLMManagerConfigurationError,
    LLMManagerError,
    LLMManagerRateLimitError,
    LLMManagerStructuredOutputError,
    LLMManagerTimeoutError,
    LLMRateLimitError,
    LLMStructuredOutputError,
)
from domain.models.overall_models.common import Role
from domain.models.overall_models.message import Message
from domain.models.overall_models.response import LLMResponse
from domain.models.overall_models.token_usage import TokenUsage
from domain.ports.llm_port import LLMPort


class _StructuredResponse(BaseModel):
    value: str


def _response(model_name: str, content: str = "ok") -> LLMResponse:
    return LLMResponse(
        content=content,
        model_name=model_name,
        finish_reason="stop",
        usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


class _ScriptedPort(LLMPort):
    def __init__(self, outcomes, model_name: str):
        self._outcomes = list(outcomes)
        self.model_name = model_name
        self.calls = 0
        self.prompts = []

    async def generate_response(self, system_prompt, messages, context=None, response_model=None):
        self.calls += 1
        self.prompts.append(system_prompt)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "timeout":
            await asyncio.sleep(0.02)
            return _response(self.model_name)
        return outcome

    async def generate_stream(self, messages, context=None):
        raise NotImplementedError()


class LLMManagerResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_generate_response_retries_same_port_before_succeeding(self):
        primary = _ScriptedPort(
            [LLMAdapterError("transient"), _response("primary")],
            model_name="primary",
        )
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=1,
            retry_backoff_seconds=0.0,
        )

        response = await manager.generate_response(
            system_prompt="system",
            messages=[Message(role=Role.USER, content="hello")],
        )

        self.assertEqual(response.model_name, "primary")
        self.assertEqual(primary.calls, 2)

    async def test_generate_response_tracks_retry_and_success_outcomes(self):
        primary = _ScriptedPort(
            [LLMAdapterError("transient"), _response("primary")],
            model_name="primary",
        )
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=1,
            retry_backoff_seconds=0.0,
        )

        with patch("application.stateless_services.llm_manager.LLMMetricsTracker.track_manager_attempt") as attempt_metric, \
             patch("application.stateless_services.llm_manager.LLMMetricsTracker.track_manager_outcome") as outcome_metric:
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

        self.assertEqual(attempt_metric.call_count, 2)
        self.assertEqual(outcome_metric.call_args_list[0].args[2], "adapter_error")
        self.assertEqual(outcome_metric.call_args_list[1].args[2], "success")

    async def test_generate_response_falls_back_after_primary_exhausts_retries(self):
        primary = _ScriptedPort(
            [LLMAdapterError("boom"), LLMAdapterError("boom again")],
            model_name="primary",
        )
        fallback = _ScriptedPort([_response("fallback")], model_name="fallback")
        manager = LLMManager(
            llm_port=primary,
            fallback_ports=[fallback],
            timeout_seconds=0.01,
            max_retries=1,
            retry_backoff_seconds=0.0,
        )

        response = await manager.generate_response(
            system_prompt="system",
            messages=[Message(role=Role.USER, content="hello")],
        )

        self.assertEqual(response.model_name, "fallback")
        self.assertEqual(primary.calls, 2)
        self.assertEqual(fallback.calls, 1)

    async def test_generate_response_tracks_fallback_switch(self):
        primary = _ScriptedPort([LLMAdapterError("boom")], model_name="primary")
        fallback = _ScriptedPort([_response("fallback")], model_name="fallback")
        manager = LLMManager(
            llm_port=primary,
            fallback_ports=[fallback],
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with patch("application.stateless_services.llm_manager.LLMMetricsTracker.track_manager_outcome") as outcome_metric:
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

        self.assertTrue(any(call.args[2] == "fallback_switch" for call in outcome_metric.call_args_list))
        self.assertTrue(any(call.args[2] == "success" for call in outcome_metric.call_args_list))

    async def test_generate_response_uses_fallback_after_timeout(self):
        primary = _ScriptedPort(["timeout"], model_name="primary")
        fallback = _ScriptedPort([_response("fallback")], model_name="fallback")
        manager = LLMManager(
            llm_port=primary,
            fallback_ports=[fallback],
            timeout_seconds=0.001,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        response = await manager.generate_response(
            system_prompt="system",
            messages=[Message(role=Role.USER, content="hello")],
        )

        self.assertEqual(response.model_name, "fallback")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    async def test_generate_response_raises_after_all_ports_fail(self):
        primary = _ScriptedPort([LLMAdapterError("boom")], model_name="primary")
        fallback = _ScriptedPort([LLMAdapterError("still boom")], model_name="fallback")
        manager = LLMManager(
            llm_port=primary,
            fallback_ports=[fallback],
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with self.assertRaises(LLMManagerError):
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

    async def test_generate_response_preserves_rate_limit_category(self):
        primary = _ScriptedPort([LLMRateLimitError("slow down")], model_name="primary")
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with self.assertRaises(LLMManagerRateLimitError):
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

    async def test_generate_response_preserves_configuration_category(self):
        primary = _ScriptedPort([LLMConfigurationError("bad model")], model_name="primary")
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with self.assertRaises(LLMManagerConfigurationError):
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

    async def test_generate_response_preserves_structured_output_category(self):
        primary = _ScriptedPort([LLMStructuredOutputError("schema broke")], model_name="primary")
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with self.assertRaises(LLMManagerStructuredOutputError):
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

    async def test_generate_response_preserves_timeout_category(self):
        primary = _ScriptedPort(["timeout"], model_name="primary")
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.001,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with self.assertRaises(LLMManagerTimeoutError):
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
            )

    async def test_generate_response_repairs_structured_output_once_before_fallback(self):
        primary = _ScriptedPort(
            [LLMStructuredOutputError("schema broke"), _response("primary", content={"value": "fixed"})],
            model_name="primary",
        )
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        response = await manager.generate_response(
            system_prompt="system",
            messages=[Message(role=Role.USER, content="hello")],
            response_model=_StructuredResponse,
        )

        self.assertEqual(response.model_name, "primary")
        self.assertEqual(primary.calls, 2)
        self.assertIn("[STRUCTURED_OUTPUT_REPAIR]", primary.prompts[1])

    async def test_generate_response_tracks_repair_attempt_and_success(self):
        primary = _ScriptedPort(
            [LLMStructuredOutputError("schema broke"), _response("primary", content={"value": "fixed"})],
            model_name="primary",
        )
        manager = LLMManager(
            llm_port=primary,
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        with patch("application.stateless_services.llm_manager.LLMMetricsTracker.track_manager_attempt") as attempt_metric, \
             patch("application.stateless_services.llm_manager.LLMMetricsTracker.track_manager_outcome") as outcome_metric:
            await manager.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="hello")],
                response_model=_StructuredResponse,
            )

        self.assertEqual(attempt_metric.call_args_list[1].kwargs["attempt_kind"], "repair")
        self.assertTrue(any(call.args[2] == "repair_success" for call in outcome_metric.call_args_list))

    async def test_generate_response_falls_back_after_structured_output_repair_fails(self):
        primary = _ScriptedPort(
            [LLMStructuredOutputError("schema broke"), LLMStructuredOutputError("still broken")],
            model_name="primary",
        )
        fallback = _ScriptedPort([_response("fallback", content={"value": "ok"})], model_name="fallback")
        manager = LLMManager(
            llm_port=primary,
            fallback_ports=[fallback],
            timeout_seconds=0.01,
            max_retries=0,
            retry_backoff_seconds=0.0,
        )

        response = await manager.generate_response(
            system_prompt="system",
            messages=[Message(role=Role.USER, content="hello")],
            response_model=_StructuredResponse,
        )

        self.assertEqual(response.model_name, "fallback")
        self.assertEqual(primary.calls, 2)
        self.assertEqual(fallback.calls, 1)


if __name__ == "__main__":
    unittest.main()