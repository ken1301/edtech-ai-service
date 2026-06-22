import base64
import hashlib
import hmac
import json
import unittest

from fastapi import HTTPException

from adapters.inbound.rest.auth import enforce_authenticated_user_id, get_authenticated_user


def _encode_segment(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _jwt(secret: str, payload: dict) -> str:
    header_segment = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload_segment = _encode_segment(payload)
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header_segment}.{payload_segment}.{signature}"


class _RequestState:
    pass


class _Config:
    AI_SERVICE_API_KEY = "internal-key"
    JWT_SECRET = "jwt-secret-for-tests"


class _Container:
    def config(self):
        return _Config()


class _App:
    container = _Container()


class _Request:
    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.app = _App()
        self.state = _RequestState()


class RestAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_user_is_derived_from_verified_jwt(self):
        token = _jwt(_Config.JWT_SECRET, {"sub": "user-123", "username": "alice", "role": "student"})
        request = _Request(
            headers={"X-API-Key": _Config.AI_SERVICE_API_KEY, "Authorization": f"Bearer {token}"}
        )

        authenticated_user = await get_authenticated_user(request)

        self.assertEqual(authenticated_user.user_id, "user-123")
        self.assertEqual(request.state.auth_user_id, "user-123")

    async def test_invalid_api_key_is_rejected(self):
        token = _jwt(_Config.JWT_SECRET, {"sub": "user-123"})
        request = _Request(headers={"X-API-Key": "wrong-key", "Authorization": f"Bearer {token}"})

        with self.assertRaises(HTTPException) as context:
            await get_authenticated_user(request)

        self.assertEqual(context.exception.status_code, 403)

    async def test_body_user_id_mismatch_is_rejected(self):
        with self.assertRaises(HTTPException) as context:
            enforce_authenticated_user_id("user-123", "user-456")

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()