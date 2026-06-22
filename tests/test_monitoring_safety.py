import unittest
from unittest.mock import patch

from fastapi import Response
from starlette.requests import Request

from infrastructure.monitoring.llm_metrics import LLMMetricsTracker
from infrastructure.monitoring.metrics_middleware import MetricsMiddleware


class _ExplodingMetric:
    def labels(self, **kwargs):
        raise ValueError("bad labels")


class _RecordingMetric:
    def __init__(self):
        self.calls = []

    def labels(self, **kwargs):
        self.calls.append(kwargs)
        return self

    def inc(self, value=1):
        return None

    def dec(self, value=1):
        return None

    def observe(self, value):
        return None


def _request() -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


class MonitoringSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_metrics_tracker_swallows_metric_failures(self):
        with patch("infrastructure.monitoring.llm_metrics.tokens_used", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.llm_metrics.request_cost", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.llm_metrics.tokens_per_request", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.llm_metrics.cost_per_request", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.llm_metrics.llm_response_latency", new=_ExplodingMetric()):
            LLMMetricsTracker.track_request(
                model="gpt-test",
                input_tokens=10,
                output_tokens=20,
                input_cost=0.01,
                output_cost=0.02,
                response_time=0.5,
            )

    async def test_metrics_middleware_returns_response_when_metrics_fail(self):
        middleware = MetricsMiddleware(app=lambda scope, receive, send: None)

        async def call_next(request):
            return Response(content="ok", status_code=200)

        with patch("infrastructure.monitoring.metrics_middleware.active_requests", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.metrics_middleware.request_count", new=_ExplodingMetric()), \
             patch("infrastructure.monitoring.metrics_middleware.request_latency", new=_ExplodingMetric()):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 200)

    async def test_metrics_middleware_counts_handled_422_response_as_error(self):
        middleware = MetricsMiddleware(app=lambda scope, receive, send: None)
        request_errors = _RecordingMetric()

        async def call_next(request):
            return Response(content="bad", status_code=422)

        with patch("infrastructure.monitoring.metrics_middleware.request_errors", new=request_errors):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 422)
        self.assertIn(
            {"method": "GET", "endpoint": "/health", "error_type": "http_422"},
            request_errors.calls,
        )

    async def test_metrics_middleware_counts_handled_500_response_as_error(self):
        middleware = MetricsMiddleware(app=lambda scope, receive, send: None)
        request_errors = _RecordingMetric()

        async def call_next(request):
            return Response(content="oops", status_code=500)

        with patch("infrastructure.monitoring.metrics_middleware.request_errors", new=request_errors):
            response = await middleware.dispatch(_request(), call_next)

        self.assertEqual(response.status_code, 500)
        self.assertIn(
            {"method": "GET", "endpoint": "/health", "error_type": "http_500"},
            request_errors.calls,
        )


if __name__ == "__main__":
    unittest.main()