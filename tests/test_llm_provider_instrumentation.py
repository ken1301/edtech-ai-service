import unittest
from unittest.mock import patch

from adapters.outbound.llm.providers.groq_adapter import GroqAdapter
from adapters.outbound.llm.providers.openai_adapter import OpenaiAdapter
from domain.models.overall_models.common import Role
from domain.models.overall_models.message import Message


class LLMProviderInstrumentationTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_adapter_logs_prompt_diagnostics_before_request(self):
        adapter = OpenaiAdapter(api_key="test-key", model="gpt-5.4-mini")

        with patch.object(adapter, "_generate_plain", return_value="ok") as generate_plain, patch(
            "adapters.outbound.llm.providers.openai_adapter.logger.debug"
        ) as debug_log:
            await adapter.generate_response(
                system_prompt="system instructions",
                messages=[Message(role=Role.USER, content="hello world")],
            )

        generate_plain.assert_called_once()
        started_call = debug_log.call_args_list[0]
        self.assertEqual(started_call.args[0], "openai_adapter.generate_response.started")
        self.assertEqual(started_call.kwargs["model"], "gpt-5.4-mini")
        self.assertFalse(started_call.kwargs["structured_output"])
        self.assertEqual(started_call.kwargs["message_count"], 2)
        self.assertEqual(started_call.kwargs["system_prompt_chars"], len("system instructions"))
        self.assertEqual(started_call.kwargs["message_chars"], len("hello world"))
        self.assertEqual(started_call.kwargs["total_input_chars"], len("system instructionshello world"))
        self.assertGreater(started_call.kwargs["estimated_input_tokens"], 0)

    async def test_groq_adapter_logs_structured_prompt_diagnostics_before_request(self):
        adapter = GroqAdapter(api_key="test-key", model="llama-3.1-8b-instant")

        class _StructuredResponse:
            __name__ = "StructuredResponse"

        with patch.object(adapter, "_generate_structured", return_value="ok") as generate_structured, patch(
            "adapters.outbound.llm.providers.groq_adapter.logger.debug"
        ) as debug_log:
            await adapter.generate_response(
                system_prompt="system",
                messages=[Message(role=Role.USER, content="student answer")],
                response_model=_StructuredResponse,
            )

        generate_structured.assert_called_once()
        started_call = debug_log.call_args_list[0]
        self.assertEqual(started_call.args[0], "groq_adapter.generate_response.started")
        self.assertTrue(started_call.kwargs["structured_output"])
        self.assertEqual(started_call.kwargs["response_model"], "StructuredResponse")
        self.assertEqual(started_call.kwargs["message_count"], 2)
        self.assertEqual(started_call.kwargs["message_chars"], len("student answer"))


if __name__ == "__main__":
    unittest.main()