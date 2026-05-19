import uuid
import structlog
import json
import base64
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SocraticContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        user_id = self._extract_user_id(request)
        
        structlog.contextvars.clear_contextvars()
        context_data = {"correlation_id": correlation_id}
        if user_id:
            context_data["user_id"] = user_id
        structlog.contextvars.bind_contextvars(**context_data)
        
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            if user_id:
                response.headers["X-User-ID"] = user_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
    
    def _extract_user_id(self, request: Request) -> str | None:
        """Extract user_id from headers or JWT token"""
        # Try to get from custom header first
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Try to extract from JWT token in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header[7:]  # Remove "Bearer " prefix
                # JWT format: header.payload.signature
                parts = token.split(".")
                if len(parts) == 3:
                    # Decode payload (add padding if needed)
                    payload = parts[1]
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += "=" * padding
                    decoded = base64.urlsafe_b64decode(payload)
                    payload_data = json.loads(decoded)
                    # Extract user_id from common JWT claims
                    return payload_data.get("sub") or payload_data.get("user_id") or payload_data.get("uid")
            except Exception:
                pass
        
        return None