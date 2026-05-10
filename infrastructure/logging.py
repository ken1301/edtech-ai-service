import logging
import structlog
from logging.handlers import RotatingFileHandler


def setup_logging(log_level: str = "INFO", log_file: str = "app.log"):
    
    # --- Standard library logging (nơi structlog ghi vào) ---
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter("%(message)s"))  # structlog đã format rồi

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    logging.basicConfig(
        handlers=[file_handler, console_handler],
        level=getattr(logging, log_level.upper(), logging.INFO),
        force=True,
    )

    # --- Shared processors cho cả dev lẫn prod ---
    shared_processors = [
        structlog.contextvars.merge_contextvars,        # tự inject correlation_id và mọi thứ đã bind
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,               # biết log từ file nào
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),       # render stack trace
        structlog.processors.ExceptionRenderer(),       # render exception vào JSON
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.processors.JSONRenderer(),        # output JSON cho prod
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()