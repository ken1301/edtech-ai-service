import logging
import structlog
from logging.handlers import RotatingFileHandler

from infrastructure.observability.middleware import correlation_id_ctx


def _inject_correlation_id(logger, method, event_dict):
    event_dict["correlation_id"] = correlation_id_ctx.get()
    return event_dict


def setup_logging():
    file_handler = RotatingFileHandler(
        "app.log", maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
    )

    logging.basicConfig(
        handlers=[file_handler, logging.StreamHandler()], # Ghi cả vào file và console
        level=logging.INFO
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _inject_correlation_id,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()