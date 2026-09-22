import logging
import json
import re
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional

# Context variables for distributed request and case tracing
request_id_ctx: ContextVar[str] = ContextVar("request_id_ctx", default="system")
case_id_ctx: ContextVar[Optional[str]] = ContextVar("case_id_ctx", default=None)
org_id_ctx: ContextVar[str] = ContextVar("org_id_ctx", default="org-novacart-main")

# Regex patterns for sensitive data redaction in logs
SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(["\']?(?:password|token|secret|authorization|api_key|access_token)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])'), r'\1[REDACTED]\3'),
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), r'[CARD_REDACTED]'),
    (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'Bearer [TOKEN_REDACTED]'),
]

class SensitiveDataFilter(logging.Filter):
    """Filters and sanitizes sensitive data (passwords, tokens, credit card numbers) from log messages."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True

class StructuredJsonFormatter(logging.Formatter):
    """Outputs log records formatted as structured JSON for log collectors (e.g. Datadog, ELK, CloudWatch)."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "case_id": case_id_ctx.get(),
            "org_id": org_id_ctx.get(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logger(name: str = "supportos") -> logging.Logger:
    """Configures and returns a logger instance with sensitive data filtering and structured format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [req:%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)
    return logger

class RequestContextLogger:
    """Adapter that dynamically injects request_id and case_id into log records."""
    def __init__(self, base_logger: logging.Logger):
        self.logger = base_logger

    def _log(self, level: int, msg: str, *args, **kwargs):
        extra = kwargs.pop("extra", {})
        extra.setdefault("request_id", request_id_ctx.get())
        extra.setdefault("case_id", case_id_ctx.get())
        kwargs["extra"] = extra
        self.logger.log(level, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

# Global logger instance
logger = RequestContextLogger(setup_logger())
