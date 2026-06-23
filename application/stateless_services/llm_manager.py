import asyncio
import json
import random
from typing import Optional, Sequence
from pydantic import BaseModel

from domain.ports.llm_port import LLMPort

from domain.models.overall_models.response import LLMResponse
from domain.models.overall_models.message import Message, ConversationContext

from infrastructure.logging import logger
from infrastructure.monitoring.llm_metrics import LLMMetricsTracker

from domain.exceptions import (
    LLMAdapterError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMManagerAuthenticationError,
    LLMManagerConfigurationError,
    LLMManagerError,
    LLMManagerProviderError,
    LLMManagerRateLimitError,
    LLMManagerStructuredOutputError,
    LLMManagerTimeoutError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStructuredOutputError,
)

class LLMManager:
    """Service responsible for handling chat-related operations, such as generating chatbot responses and managing conversation context."""

    def __init__(
        self,
        llm_port: LLMPort,
        fallback_ports: Optional[Sequence[LLMPort]] = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 1,
        retry_backoff_seconds: float = 0.1,
    ):
        self._llm_port = llm_port
        self._fallback_ports = tuple(fallback_ports or ())
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def _ports(self) -> tuple[LLMPort, ...]:
        return (self._llm_port, *self._fallback_ports)

    @staticmethod
    def _repair_prompt(system_prompt: str, response_model: type[BaseModel]) -> str:
        schema_payload = json.dumps(
            response_model.model_json_schema(),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return (
            system_prompt
            + "\n\n[STRUCTURED_OUTPUT_REPAIR]\n"
            + "The previous response failed schema validation. Retry once and return only a valid structured response. "
            + "Do not include markdown, prose, or extra keys. Respect required fields, enum values, and numeric bounds.\n"
            + f"Target schema for {response_model.__name__}: {schema_payload}"
        )

    async def _invoke_port(
        self,
        llm_port: LLMPort,
        system_prompt: str,
        messages: list[Message],
        conversation_context: Optional[ConversationContext],
        response_model: Optional[BaseModel],
    ) -> LLMResponse:
        return await asyncio.wait_for(
            llm_port.generate_response(
                system_prompt=system_prompt,
                messages=messages,
                context=conversation_context,
                response_model=response_model,
            ),
            timeout=self._timeout_seconds,
        )

    async def _sleep_before_retry(self, attempt_index: int) -> None:
        if self._retry_backoff_seconds <= 0:
            return
        base_delay = self._retry_backoff_seconds * attempt_index
        await asyncio.sleep(base_delay + random.uniform(0.0, self._retry_backoff_seconds))

    @staticmethod
    def _raise_manager_error(last_error: Exception) -> None:
        if isinstance(last_error, asyncio.TimeoutError):
            raise LLMManagerTimeoutError("LLM request timed out after all retries and fallbacks.") from last_error
        if isinstance(last_error, LLMRateLimitError):
            raise LLMManagerRateLimitError("LLM requests were rate-limited after all retries and fallbacks.") from last_error
        if isinstance(last_error, LLMAuthenticationError):
            raise LLMManagerAuthenticationError("LLM authentication failed after all retries and fallbacks.") from last_error
        if isinstance(last_error, LLMConfigurationError):
            raise LLMManagerConfigurationError("LLM configuration or request parameters are invalid.") from last_error
        if isinstance(last_error, LLMStructuredOutputError):
            raise LLMManagerStructuredOutputError("Structured output generation failed after all retries and fallbacks.") from last_error
        if isinstance(last_error, LLMProviderError):
            raise LLMManagerProviderError("LLM provider failed after all retries and fallbacks.") from last_error
        if isinstance(last_error, LLMAdapterError):
            raise LLMManagerError("Failed to generate chatbot response from LLM after all retries and fallbacks.") from last_error
        raise LLMManagerError("Failed to generate response from LLM.")

    @staticmethod
    def _outcome_name(error: Exception) -> str:
        if isinstance(error, asyncio.TimeoutError):
            return "timeout"
        if isinstance(error, LLMRateLimitError):
            return "rate_limit"
        if isinstance(error, LLMAuthenticationError):
            return "authentication_error"
        if isinstance(error, LLMConfigurationError):
            return "configuration_error"
        if isinstance(error, LLMStructuredOutputError):
            return "structured_output_error"
        if isinstance(error, LLMProviderError):
            return "provider_error"
        if isinstance(error, LLMAdapterError):
            return "adapter_error"
        return "unknown_error"

    async def generate_response(
        self,
        system_prompt: str,
        messages: list[Message],
        conversation_context: Optional[ConversationContext] = None,
        response_model: Optional[BaseModel] = None
    ) -> LLMResponse:
        """Generate a chatbot response based on the conversation history and context."""
        last_error: Exception | None = None

        for port_index, llm_port in enumerate(self._ports()):
            for attempt in range(1, self._max_retries + 2):
                LLMMetricsTracker.track_manager_attempt(
                    llm_port=llm_port,
                    used_fallback=port_index > 0,
                    attempt_kind="retry" if attempt > 1 else "initial",
                    response_model=response_model,
                )
                try:
                    llm_response = await self._invoke_port(
                        llm_port=llm_port,
                        system_prompt=system_prompt,
                        messages=messages,
                        conversation_context=conversation_context,
                        response_model=response_model,
                    )

                    logger.info(
                        "llm_manager.generate_response.completed",
                        log_type="business",
                        model_name=llm_response.model_name,
                        attempt=attempt,
                        used_fallback=port_index > 0,
                    )
                    LLMMetricsTracker.track_manager_outcome(llm_port, port_index > 0, "success")

                    return llm_response

                except asyncio.TimeoutError as e:
                    last_error = e
                    LLMMetricsTracker.track_manager_outcome(
                        llm_port,
                        port_index > 0,
                        self._outcome_name(e),
                    )
                    logger.warning(
                        "llm_manager.generate_response.timeout",
                        log_type="technical",
                        attempt=attempt,
                        used_fallback=port_index > 0,
                        timeout_seconds=self._timeout_seconds,
                    )
                except LLMStructuredOutputError as e:
                    last_error = e
                    LLMMetricsTracker.track_manager_outcome(
                        llm_port,
                        port_index > 0,
                        self._outcome_name(e),
                    )
                    logger.warning(
                        "llm_manager.generate_response.structured_output_failed",
                        log_type="technical",
                        attempt=attempt,
                        used_fallback=port_index > 0,
                        error=str(e),
                    )

                    if response_model is not None:
                        try:
                            LLMMetricsTracker.track_manager_attempt(
                                llm_port=llm_port,
                                used_fallback=port_index > 0,
                                attempt_kind="repair",
                                response_model=response_model,
                            )
                            repaired_response = await self._invoke_port(
                                llm_port=llm_port,
                                system_prompt=self._repair_prompt(system_prompt, response_model),
                                messages=messages,
                                conversation_context=conversation_context,
                                response_model=response_model,
                            )

                            logger.info(
                                "llm_manager.generate_response.structured_output_repaired",
                                log_type="business",
                                model_name=repaired_response.model_name,
                                attempt=attempt,
                                used_fallback=port_index > 0,
                            )
                            LLMMetricsTracker.track_manager_outcome(llm_port, port_index > 0, "repair_success")

                            return repaired_response
                        except asyncio.TimeoutError as repair_error:
                            last_error = repair_error
                            LLMMetricsTracker.track_manager_outcome(
                                llm_port,
                                port_index > 0,
                                "repair_timeout",
                            )
                            logger.warning(
                                "llm_manager.generate_response.structured_output_repair_timeout",
                                log_type="technical",
                                attempt=attempt,
                                used_fallback=port_index > 0,
                                timeout_seconds=self._timeout_seconds,
                            )
                        except LLMAdapterError as repair_error:
                            last_error = repair_error
                            LLMMetricsTracker.track_manager_outcome(
                                llm_port,
                                port_index > 0,
                                "repair_failure",
                            )
                            logger.warning(
                                "llm_manager.generate_response.structured_output_repair_failed",
                                log_type="technical",
                                attempt=attempt,
                                used_fallback=port_index > 0,
                                error=str(repair_error),
                            )
                except LLMAdapterError as e:
                    last_error = e
                    LLMMetricsTracker.track_manager_outcome(
                        llm_port,
                        port_index > 0,
                        self._outcome_name(e),
                    )
                    logger.warning(
                        "llm_manager.generate_response.adapter_failed",
                        log_type="technical",
                        attempt=attempt,
                        used_fallback=port_index > 0,
                        error=str(e),
                    )
                except Exception as e:
                    logger.error(
                        "llm_manager.generate_response.unexpected.failed",
                        log_type="technical",
                        attempt=attempt,
                        used_fallback=port_index > 0,
                        error=str(e),
                        exc_info=True,
                    )
                    raise LLMManagerError("Failed to generate response from LLM.") from e

                if attempt <= self._max_retries:
                    await self._sleep_before_retry(attempt)

            if port_index + 1 < len(self._ports()):
                LLMMetricsTracker.track_manager_outcome(llm_port, port_index > 0, "fallback_switch")
                logger.warning(
                    "llm_manager.generate_response.switching_fallback",
                    log_type="technical",
                    failed_port_index=port_index,
                    next_port_index=port_index + 1,
                )

        if last_error is not None:
            self._raise_manager_error(last_error)
        raise LLMManagerError("Failed to generate response from LLM.")
        


