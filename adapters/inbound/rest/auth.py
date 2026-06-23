import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import structlog
from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: Optional[str] = None
    role: Optional[str] = None


def _decode_base64url(value: str) -> bytes:
    padding = (-len(value)) % 4
    return base64.urlsafe_b64decode(value + ("=" * padding))


def _verify_hs256_jwt(token: str, secret: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token format.",
        ) from exc

    try:
        header = json.loads(_decode_base64url(header_segment))
        payload = json.loads(_decode_base64url(payload_segment))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token payload.",
        ) from exc

    if header.get("alg") != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported bearer token algorithm.",
        )

    signing_input = f"{header_segment}.{payload_segment}".encode()
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()

    if not hmac.compare_digest(expected_signature, signature_segment):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token signature.",
        )

    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None and int(exp) <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token has expired.",
        )

    nbf = payload.get("nbf")
    if nbf is not None and int(nbf) > now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is not active yet.",
        )

    return payload


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization[7:].strip()

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing bearer token.",
    )


def _get_settings(request: Request):
    container = getattr(request.app, "container", None)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application container is not available.",
        )
    return container.config()


def _get_internal_authenticated_user(request: Request) -> Optional[AuthenticatedUser]:
    user_id = request.headers.get("X-Authenticated-User-ID")
    if not user_id:
        return None

    return AuthenticatedUser(
        user_id=user_id,
        username=request.headers.get("X-Authenticated-Username") or None,
        role=request.headers.get("X-Authenticated-Role") or None,
    )


async def get_authenticated_user(request: Request) -> AuthenticatedUser:
    settings = _get_settings(request)
    expected_api_key = settings.AI_SERVICE_API_KEY
    provided_api_key = request.headers.get("X-API-Key")

    if not provided_api_key or not hmac.compare_digest(provided_api_key, expected_api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid AI service API key.",
        )

    internal_user = _get_internal_authenticated_user(request)
    if internal_user is not None:
        request.state.auth_user_id = internal_user.user_id
        structlog.contextvars.bind_contextvars(user_id=internal_user.user_id)
        return internal_user

    token = _extract_bearer_token(request)
    payload = _verify_hs256_jwt(token, settings.JWT_SECRET)
    user_id = payload.get("sub") or payload.get("user_id") or payload.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token does not contain a user identifier.",
        )

    request.state.auth_user_id = user_id
    structlog.contextvars.bind_contextvars(user_id=user_id)
    return AuthenticatedUser(
        user_id=user_id,
        username=payload.get("username"),
        role=payload.get("role"),
    )


def enforce_authenticated_user_id(authenticated_user_id: str, body_user_id: str) -> str:
    if body_user_id and body_user_id != authenticated_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated user does not match request body user_id.",
        )
    return authenticated_user_id