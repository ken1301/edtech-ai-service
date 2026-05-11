import structlog
from infrastructure.monitoring.metrics import (
    tokens_used, request_cost, tokens_per_request,
    cost_per_request, llm_response_latency
)

logger = structlog.get_logger()


class LLMMetricsTracker:
    """Tracks LLM-specific metrics like tokens and costs."""

    @staticmethod
    def track_request(
        user_id: str,
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

        # Track tokens
        tokens_used.labels(user_id=user_id, model=model, token_type='input').inc(input_tokens)
        tokens_used.labels(user_id=user_id, model=model, token_type='output').inc(output_tokens)

        # Track cost
        request_cost.labels(user_id=user_id, model=model).inc(total_cost)

        # Record histograms
        tokens_per_request.labels(model=model).observe(total_tokens)
        cost_per_request.labels(model=model).observe(total_cost)
        llm_response_latency.labels(model=model).observe(response_time)

        logger.info(
            "llm_request_completed",
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            total_cost=total_cost,
            response_time=response_time
        )

    @staticmethod
    def track_error(user_id: str, model: str, error: str):
        """Record LLM request error."""
        logger.error(
            "llm_request_failed",
            user_id=user_id,
            model=model,
            error=error
        )
