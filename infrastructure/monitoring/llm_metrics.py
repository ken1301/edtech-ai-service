import structlog
from infrastructure.monitoring.metrics import (
    tokens_used, request_cost, tokens_per_request,
    cost_per_request, llm_response_latency,
    llm_manager_attempts, llm_manager_outcomes,
)

logger = structlog.get_logger()


class LLMMetricsTracker:
    """Tracks LLM-specific metrics like tokens and costs."""

    @staticmethod
    def _port_identity(llm_port, used_fallback: bool) -> tuple[str, str, str]:
        provider_name = llm_port.__class__.__name__
        provider = provider_name.removesuffix("Adapter").lower() or "unknown"
        model = getattr(llm_port, "model", None) or getattr(llm_port, "model_name", None) or "unknown"
        port_type = "fallback" if used_fallback else "primary"
        return provider, str(model), port_type

    @staticmethod
    def _safe_record(metric_name: str, operation, **context):
        try:
            operation()
        except Exception as e:
            logger.warning(
                "llm_metrics.record_failed",
                metric_name=metric_name,
                error=str(e),
                **context,
            )

    @staticmethod
    def track_request(
        model: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        response_time: float
    ):
        """Record metrics for an LLM request."""
        total_tokens = input_tokens + output_tokens
        total_cost = input_cost + output_cost

        LLMMetricsTracker._safe_record(
            "tokens_used_input",
            lambda: tokens_used.labels(model=model, token_type='input').inc(input_tokens),
            model=model,
        )
        LLMMetricsTracker._safe_record(
            "tokens_used_output",
            lambda: tokens_used.labels(model=model, token_type='output').inc(output_tokens),
            model=model,
        )
        LLMMetricsTracker._safe_record(
            "request_cost",
            lambda: request_cost.labels(model=model).inc(total_cost),
            model=model,
        )
        LLMMetricsTracker._safe_record(
            "tokens_per_request",
            lambda: tokens_per_request.labels(model=model).observe(total_tokens),
            model=model,
        )
        LLMMetricsTracker._safe_record(
            "cost_per_request",
            lambda: cost_per_request.labels(model=model).observe(total_cost),
            model=model,
        )
        LLMMetricsTracker._safe_record(
            "llm_response_latency",
            lambda: llm_response_latency.labels(model=model).observe(response_time),
            model=model,
        )

        logger.info(
            "llm_request_completed",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            total_cost=total_cost,
            response_time=response_time
        )

    @staticmethod
    def track_error(model: str, error: str):
        """Record LLM request error."""
        logger.error(
            "llm_request_failed",
            model=model,
            error=error
        )

    @staticmethod
    def track_manager_attempt(llm_port, used_fallback: bool, attempt_kind: str, response_model) -> None:
        provider, model, port_type = LLMMetricsTracker._port_identity(llm_port, used_fallback)
        response_format = "structured" if response_model is not None else "plain"
        LLMMetricsTracker._safe_record(
            "llm_manager_attempts",
            lambda: llm_manager_attempts.labels(
                provider=provider,
                model=model,
                port_type=port_type,
                attempt_kind=attempt_kind,
                response_format=response_format,
            ).inc(),
            provider=provider,
            model=model,
            port_type=port_type,
            attempt_kind=attempt_kind,
            response_format=response_format,
        )

    @staticmethod
    def track_manager_outcome(llm_port, used_fallback: bool, outcome: str) -> None:
        provider, model, port_type = LLMMetricsTracker._port_identity(llm_port, used_fallback)
        LLMMetricsTracker._safe_record(
            "llm_manager_outcomes",
            lambda: llm_manager_outcomes.labels(
                provider=provider,
                model=model,
                port_type=port_type,
                outcome=outcome,
            ).inc(),
            provider=provider,
            model=model,
            port_type=port_type,
            outcome=outcome,
        )
