from tracemalloc import start

import openai
from openai import AsyncOpenAI
import instructor
from instructor.exceptions import IncompleteOutputException, InstructorError, InstructorRetryException
from pydantic import BaseModel
from typing import List, Optional
import time

from domain.exceptions import LLMAdapterError
from domain.ports.llm_port import LLMPort
from domain.models.overall_models.message import Message, ConversationContext
from domain.models.overall_models.response import LLMResponse, TokenUsage

from infrastructure.logging import logger
from infrastructure.monitoring.metrics import (
    tokens_used, request_cost,
    tokens_per_request, cost_per_request,
    llm_response_latency
)


class OpenaiAdapter(LLMPort):
    """
    OpenAI LLM adapter.

    Routing strategy
    ────────────────
    • response_model is None  → plain AsyncOpenAI client
      Returns a normal ChatCompletion; content is response.choices[0].message.content.

    • response_model provided → instructor-patched client
      Returns a (parsed_model, raw_completion) tuple via create_with_completion.
      instructor handles schema injection, validation, and its own retry loop.
      If instructor exhausts its retries, InstructorRetryException bubbles up here.

    Keeping two separate clients avoids running every plain-text request through
    instructor's validation pipeline, which adds latency and non-deterministic
    retry behaviour when structured output is not needed.
    """

    input_cost_per_million = {
        "gpt-5.4-nano": 0.2,  
        "gpt-5.4-mini": 0.75,  
        "gpt-5.4": 2.5,
        "gpt-5.5": 5.0,    
    }
    output_cost_per_million = {
        "gpt-5.4-nano": 1.25,
        "gpt-5.4-mini": 4.5,
        "gpt-5.4": 15.0,
        "gpt-5.5": 30.0,
    }

    def __init__(self, api_key: str, model: str = "gpt-5.4-nano"):
        self._base_client       = AsyncOpenAI(api_key=api_key)
        self._instructor_client = instructor.from_openai(self._base_client)
        self.model              = model

    async def generate_response(
        self,
        system_prompt: str,
        messages: List[Message],
        context: Optional[ConversationContext] = None,
        response_model: Optional[BaseModel] = None,
    ) -> LLMResponse:

        formatted_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            formatted_messages.append({"role": m.role.value, "content": m.content})

        temperature = context.temperature if context else 0.3
        max_tokens  = context.max_completion_tokens if context else None

        api_params = {
            "model":                self.model,
            "messages":             formatted_messages,
            "temperature":          temperature,
            "max_completion_tokens": max_tokens,
        }

        if response_model is not None:
            return await self._generate_structured(api_params, response_model)
        return await self._generate_plain(api_params)

    # ── private helpers ───────────────────────────────────────────────────────

    async def _generate_plain(self, api_params: dict) -> LLMResponse:
        """Plain-text completion via the base AsyncOpenAI client."""
        try:
            start = time.time()
            
            completion = await self._base_client.chat.completions.create(**api_params)

            duration = time.time() - start
            usage = completion.usage

            # tính cost — ví dụ gpt-5.4-nano: $0.20 / 1M input tokens, $1.25 / 1M output tokens
            input_cost  = (usage.prompt_tokens / 1_000_000) * self.input_cost_per_million[self.model]
            output_cost = (usage.completion_tokens / 1_000_000) * self.output_cost_per_million[self.model]
            total_cost  = input_cost + output_cost

            # record metrics
            llm_response_latency.labels(model=self.model).observe(duration)

            tokens_used.labels(model=self.model, token_type="input").inc(usage.prompt_tokens)
            tokens_used.labels(model=self.model, token_type="output").inc(usage.completion_tokens)

            tokens_per_request.labels(model=self.model).observe(usage.total_tokens)

            request_cost.labels(model=self.model).inc(total_cost)
            cost_per_request.labels(model=self.model).observe(total_cost)

            logger.debug(
                "openai_adapter.plain.completed",
                log_type="debug",
                model=self.model,
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

        except openai.RateLimitError as e:
            logger.warning(
                "openai_adapter.plain.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI rate limit exceeded. Please try again later.") from e

        except openai.AuthenticationError as e:
            logger.error(
                "openai_adapter.plain.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI authentication failed. Check your API key.") from e

        except openai.BadRequestError as e:
            logger.error(
                "openai_adapter.plain.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI bad request. Check your input parameters.") from e

        except openai.OpenAIError as e:
            logger.error(
                "openai_adapter.plain.api_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI API error occurred. Please try again later.") from e

        except Exception as e:
            logger.error(
                "openai_adapter.plain.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("An unexpected error occurred while calling OpenAI API.") from e

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

            # tính cost — ví dụ gpt-5.4-nano: $0.20 / 1M input tokens, $1.25 / 1M output tokens
            input_cost  = (usage.prompt_tokens / 1_000_000) * self.input_cost_per_million[self.model]
            output_cost = (usage.completion_tokens / 1_000_000) * self.output_cost_per_million[self.model]
            total_cost  = input_cost + output_cost

            # record metrics
            llm_response_latency.labels(model=self.model).observe(duration)

            tokens_used.labels(model=self.model, token_type="input").inc(usage.prompt_tokens)
            tokens_used.labels(model=self.model, token_type="output").inc(usage.completion_tokens)

            tokens_per_request.labels(model=self.model).observe(usage.total_tokens)

            request_cost.labels(model=self.model).inc(total_cost)
            cost_per_request.labels(model=self.model).observe(total_cost)

            logger.debug(
                "openai_adapter.structured.completed",
                log_type="debug",
                model=self.model,
                response_model=response_model.__name__,
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

        # ── instructor-specific exceptions (most specific first) ──────────────

        except InstructorRetryException as e:
            # All of instructor's internal retries have been exhausted.
            # This is a hard failure, not a transient warning.
            logger.error(
                "openai_adapter.structured.instructor_retry_exhausted",
                log_type="technical",
                response_model=response_model.__name__,
                attempts=e.n_attempts if hasattr(e, "n_attempts") else "unknown",
                last_error=str(e),
            )
            raise LLMAdapterError(
                "Instructor failed to produce a valid structured response after all retries."
            ) from e

        except IncompleteOutputException as e:
            # Model stopped generating before completing the JSON schema —
            # usually a max_tokens issue.
            logger.warning(
                "openai_adapter.structured.incomplete_output",
                log_type="technical",
                response_model=response_model.__name__,
                error=str(e),
            )
            raise LLMAdapterError(
                "Model output was cut off before the structured response was complete. "
                "Consider increasing max_completion_tokens."
            ) from e

        except InstructorError as e:
            # Catch-all for other instructor failures (schema injection, etc.)
            logger.error(
                "openai_adapter.structured.instructor_error",
                log_type="technical",
                response_model=response_model.__name__,
                error=str(e),
            )
            raise LLMAdapterError("Instructor encountered an error processing the structured request.") from e

        # ── OpenAI API exceptions ─────────────────────────────────────────────

        except openai.RateLimitError as e:
            logger.warning(
                "openai_adapter.structured.rate_limit",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI rate limit exceeded. Please try again later.") from e

        except openai.AuthenticationError as e:
            logger.error(
                "openai_adapter.structured.authentication_failed",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI authentication failed. Check your API key.") from e

        except openai.BadRequestError as e:
            logger.error(
                "openai_adapter.structured.bad_request",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI bad request. Check your input parameters.") from e

        except openai.OpenAIError as e:
            logger.error(
                "openai_adapter.structured.api_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("OpenAI API error occurred. Please try again later.") from e

        except Exception as e:
            logger.error(
                "openai_adapter.structured.unknown_error",
                log_type="technical",
                error=str(e),
            )
            raise LLMAdapterError("An unexpected error occurred while calling OpenAI API.") from e

    async def generate_stream(
        self,
        messages: List[Message],
        context: Optional[ConversationContext] = None,
    ):
        raise NotImplementedError("Streaming support coming soon.")