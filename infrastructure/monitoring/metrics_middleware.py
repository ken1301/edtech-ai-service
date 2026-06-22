import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from infrastructure.monitoring.metrics import (
    request_count, request_latency, request_errors, active_requests
)

logger = structlog.get_logger()


class MetricsMiddleware(BaseHTTPMiddleware):
    @staticmethod
    def _safe_metric(metric_name: str, operation, **context):
        try:
            operation()
        except Exception as e:
            logger.warning(
                "metrics_middleware.metric_failed",
                metric_name=metric_name,
                error=str(e),
                **context,
            )

    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        endpoint = f"{method} {path}"

        self._safe_metric(
            "active_requests_inc",
            lambda: active_requests.labels(method=method, endpoint=path).inc(),
            method=method,
            path=path,
        )
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            logger.info(
                "request_completed",
                method=method,
                path=path,
                status_code=status_code,
                elapsed_seconds=time.time() - start_time
            )

            self._safe_metric(
                "request_count",
                lambda: request_count.labels(method=method, endpoint=path, status_code=status_code).inc(),
                method=method,
                path=path,
                status_code=status_code,
            )
            if status_code >= 400:
                self._safe_metric(
                    "request_errors_handled",
                    lambda: request_errors.labels(
                        method=method,
                        endpoint=path,
                        error_type=f"http_{status_code}",
                    ).inc(),
                    method=method,
                    path=path,
                    status_code=status_code,
                )

        except Exception as e:
            status_code = 500
            self._safe_metric(
                "request_errors",
                lambda: request_errors.labels(method=method, endpoint=path, error_type=type(e).__name__).inc(),
                method=method,
                path=path,
                error_type=type(e).__name__,
            )
            logger.error(
                "request_failed",
                method=method,
                path=path,
                error=str(e),
                elapsed_seconds=time.time() - start_time
            )
            raise

        finally:
            elapsed = time.time() - start_time
            self._safe_metric(
                "request_latency",
                lambda: request_latency.labels(method=method, endpoint=path).observe(elapsed),
                method=method,
                path=path,
            )
            self._safe_metric(
                "active_requests_dec",
                lambda: active_requests.labels(method=method, endpoint=path).dec(),
                method=method,
                path=path,
            )

        return response
