import logging
import structlog
from logging.handlers import RotatingFileHandler


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