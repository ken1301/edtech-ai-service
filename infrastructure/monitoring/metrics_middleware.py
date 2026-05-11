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
    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path
        endpoint = f"{method} {path}"

        active_requests.labels(method=method, endpoint=path).inc()
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

            request_count.labels(method=method, endpoint=path, status_code=status_code).inc()

        except Exception as e:
            status_code = 500
            request_errors.labels(method=method, endpoint=path, error_type=type(e).__name__).inc()
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
            request_latency.labels(method=method, endpoint=path).observe(elapsed)
            active_requests.labels(method=method, endpoint=path).dec()

        return response
