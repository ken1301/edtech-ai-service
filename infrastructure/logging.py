import logging
import re
import structlog
from logging.handlers import RotatingFileHandler


REDACTED = "<redacted>"
URL_REDACTED = "<redacted:url>"
KEY_REDACTED = "<redacted:key>"

_SENSITIVE_FIELD_TOKENS = (
    "authorization",
    "token",
    "api_key",
    "secret",
    "password",
    "prompt",
    "message",
    "msg",
    "content",
    "answer",
    "submission",
    "document_url",
    "access_token",
    "refresh_token",
    "signed_url",
    "object_key",
)
_URL_QUERY_SECRET_RE = re.compile(r"(x-amz-signature|x-amz-credential|x-amz-security-token|signature|token)=", re.IGNORECASE)
_USER_OBJECT_KEY_RE = re.compile(r"(^|/)(users/[^\s]+)")


def _is_sensitive_key(key: str) -> bool:
    normalized = key.strip().lower()
    return any(token in normalized for token in _SENSITIVE_FIELD_TOKENS)


def _sanitize_string(value: str) -> str:
    lower_value = value.lower()
    if lower_value.startswith(("http://", "https://")):
        return URL_REDACTED
    if _URL_QUERY_SECRET_RE.search(value):
        return URL_REDACTED
    if _USER_OBJECT_KEY_RE.search(value):
        return KEY_REDACTED
    return value


def _redact_value(key: str | None, value):
    if key is not None and _is_sensitive_key(key):
        if isinstance(value, str) and (value.lower().startswith(("http://", "https://")) or _URL_QUERY_SECRET_RE.search(value)):
            return URL_REDACTED
        if isinstance(value, str) and _USER_OBJECT_KEY_RE.search(value):
            return KEY_REDACTED
        return REDACTED

    if isinstance(value, dict):
        return {nested_key: _redact_value(str(nested_key), nested_value) for nested_key, nested_value in value.items()}

    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]

    if isinstance(value, tuple):
        return tuple(_redact_value(key, item) for item in value)

    if isinstance(value, str):
        return _sanitize_string(value)

    return value


def redact_event_dict(logger, method_name, event_dict):
    return {key: _redact_value(str(key), value) for key, value in event_dict.items()}


def setup_logging(log_level: str = "INFO", log_file: str = "app.log"):
    # 1. Lấy đúng giá trị level từ string (ví dụ: "DEBUG" -> 10)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # --- Standard library logging ---
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(
        handlers=[file_handler, console_handler],
        level=numeric_level,  # Áp dụng level cho stdlib
        force=True,
    )

    # --- Shared processors ---
    shared_processors = [
        # Chú ý: Đặt filter_by_level lên ĐẦU TIÊN để drop log sớm, đỡ tốn hiệu năng xử lý phía sau
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(), # Cần thiết cho filter_by_level hoạt động tốt
        redact_event_dict,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

logger = structlog.get_logger()