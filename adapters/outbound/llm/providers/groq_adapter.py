import groq
from groq import AsyncGroq
import instructor
from instructor.exceptions import IncompleteOutputException, InstructorError, InstructorRetryException
from pydantic import BaseModel
from typing import List, Optional
import time

from domain.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStructuredOutputError,
)
from domain.ports.llm_port import LLMPort

from domain.models.overall_models.message import Message, ConversationContext
from domain.models.overall_models.response import LLMResponse, TokenUsage

from infrastructure.logging import logger
from infrastructure.monitoring.llm_metrics import LLMMetricsTracker

class GroqAdapter(LLMPort):
    """
    Groq LLM adapter.

    Routing strategy
    ────────────────
    • response_model is None  → plain AsyncGroq client
      Returns a normal ChatCompletion; content is completion.choices[0].message.content.

    • response_model provided → instructor-patched client
      Returns a (parsed_model, raw_completion) tuple via create_with_completion.
      instructor handles schema injection, validation, and its own retry loop.
      If instructor exhausts its retries, InstructorRetryException bubbles up here.

    Keeping two separate clients avoids running every plain-text request through
    instructor's validation pipeline, which adds latency and non-deterministic
    retry behaviour when structured output is not needed.
    """

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        self._base_client = AsyncGroq(api_key=api_key)
        self._instructor_client = instructor.from_groq(self._base_client)
        self.model = model
        self.input_cost_per_million = {}
        self.output_cost_per_million = {}

    def _token_costs(self, usage) -> tuple[float, float]:
        input_cost_per_million = self.input_cost_per_million.get(self.model, 0.0)
        output_cost_per_million = self.output_cost_per_million.get(self.model, 0.0)
        input_cost = (usage.prompt_tokens / 1_000_000) * input_cost_per_million
        output_cost = (usage.completion_tokens / 1_000_000) * output_cost_per_million
        return input_cost, output_cost

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Message],
        context: Optional[ConversationContext] = None,
        response_model: Optional[BaseModel] = None,
    ) -> LLMResponse:
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for message in messages:
            formatted_messages.append({"role": message.role.value, "content": message.content})

        temperature = context.temperature if context else 0.3
        max_tokens = context.max_completion_tokens if context else None

        api_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_model is not None:
            return await self._generate_structured(api_params, response_model)
        return await self._generate_plain(api_params)

    # ── private helpers ───────────────────────────────────────────────────────

    async def _generate_plain(self, api_params: dict) -> LLMResponse:
        """Plain-text completion via the base AsyncGroq client."""
        try:
            start = time.time()
            completion = await self._base_client.chat.completions.create(**api_params)
            duration = time.time() - start
            usage = completion.usage
            input_cost, output_cost = self._token_costs(usage)
            LLMMetricsTracker.track_request(
                model=self.model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                response_time=duration,
            )

            return LLMResponse(
                content=completion.choices[0].message.content,
                model_name=self.model,
                finish_reason=completion.choices[0].finish_reason,
                usage=TokenUsage(
                    prompt_tokens=completion.usage.prompt_tokens,
                    completion_tokens=completion.usage.completion_tokens,
                    total_tokens=completion.usage.total_tokens,
                ),
            )

        except groq.RateLimitError as e:
            logger.warning(
                "groq_adapter.plain.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMRateLimitError("Groq API rate limit exceeded. Please try again later.") from e

        except groq.AuthenticationError as e:
            logger.error(
                "groq_adapter.plain.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMAuthenticationError("Groq API authentication failed. Check your API key.") from e

        except groq.BadRequestError as e:
            logger.error(
                "groq_adapter.plain.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMConfigurationError("Groq API bad request. Check your input parameters.") from e

        except groq.APIError as e:
            logger.error(
                "groq_adapter.plain.api_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMProviderError("Groq API error occurred. Please try again later.") from e

        except Exception as e:
            logger.error(
                "groq_adapter.plain.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMProviderError("An unexpected error occurred while calling Groq API.") from e

    async def _generate_structured(
        self,
        api_params: dict,
        response_model: type[BaseModel],
    ) -> LLMResponse:
        """
        Structured completion via the instructor-patched client.

        Exception hierarchy (most specific → most general):
            InstructorRetryException  ← instructor exhausted all retries
            IncompleteOutputException ← model hit token limit mid-schema
            InstructorError           ← base class, other instructor failures
        """
        try:
            start = time.time()
            parsed, completion = await self._instructor_client.chat.completions.create_with_completion(
                **api_params,
                response_model=response_model,
            )
            duration = time.time() - start
            usage = completion.usage
            input_cost, output_cost = self._token_costs(usage)
            LLMMetricsTracker.track_request(
                model=self.model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                response_time=duration,
            )

            return LLMResponse(
                content=parsed,
                model_name=self.model,
                finish_reason=completion.choices[0].finish_reason,
                usage=TokenUsage(
                    prompt_tokens=completion.usage.prompt_tokens,
                    completion_tokens=completion.usage.completion_tokens,
                    total_tokens=completion.usage.total_tokens,
                ),
            )

        except InstructorRetryException as e:
            logger.error(
                "groq_adapter.structured.instructor_retry_exhausted",
                log_type="technical",
                response_model=response_model.__name__,
                attempts=e.n_attempts if hasattr(e, "n_attempts") else "unknown",
                last_error=str(e),
            )
            raise LLMStructuredOutputError(
                "Instructor failed to produce a valid structured response after all retries."
            ) from e

        except IncompleteOutputException as e:
            logger.warning(
                "groq_adapter.structured.incomplete_output",
                log_type="technical",
                response_model=response_model.__name__,
                error=str(e),
            )
            raise LLMStructuredOutputError(
                "Model output was cut off before the structured response was complete. "
                "Consider increasing max_tokens."
            ) from e

        except InstructorError as e:
            logger.error(
                "groq_adapter.structured.instructor_error",
                log_type="technical",
                response_model=response_model.__name__,
                error=str(e),
            )
            raise LLMStructuredOutputError("Instructor encountered an error processing the structured request.") from e

        except groq.RateLimitError as e:
            logger.warning(
                "groq_adapter.structured.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMRateLimitError("Groq API rate limit exceeded. Please try again later.") from e

        except groq.AuthenticationError as e:
            logger.error(
                "groq_adapter.structured.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMAuthenticationError("Groq API authentication failed. Check your API key.") from e

        except groq.BadRequestError as e:
            logger.error(
                "groq_adapter.structured.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMConfigurationError("Groq API bad request. Check your input parameters.") from e

        except groq.APIError as e:
            logger.error(
                "groq_adapter.structured.api_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMProviderError("Groq API error occurred. Please try again later.") from e

        except Exception as e:
            logger.error(
                "groq_adapter.structured.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMProviderError("An unexpected error occurred while calling Groq API.") from e

    async def generate_stream(
        self,
        messages: List[Message],
        context: Optional[ConversationContext] = None,
    ):
        raise NotImplementedError("Streaming support coming soon.")