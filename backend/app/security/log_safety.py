"""Privacy helpers for application logs."""

import hashlib
import logging
import re


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_LONG_DIGITS = re.compile(r"\b\d{7,}\b")


def privacy_fingerprint(value: str) -> str:
    """Return a stable short reference without logging the supplied text/name."""
    return hashlib.sha256((value or "").encode("utf-8", errors="replace")).hexdigest()[:12]


_BEARER_TOKEN = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.]+", re.IGNORECASE)
_JWT_TOKEN = re.compile(r"\beyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_.]+\b")
_API_KEY_KV = re.compile(r"(?i)\b(api[_-]?key|password|secret|access[_-]?token|refresh[_-]?token|private[_-]?key)\s*([:=])\s*['\"]?[A-Za-z0-9\-_.]{8,}['\"]?")
_GENERIC_KEY_PATTERN = re.compile(r"\b(gsk_|AIzaSy|sk-)[A-Za-z0-9\-_]{16,}\b")


def redact_log_text(value: str) -> str:
    if not value:
        return ""
    text = _EMAIL.sub("[REDACTED_EMAIL]", str(value))
    text = _BEARER_TOKEN.sub(r"\1[REDACTED_TOKEN]", text)
    text = _JWT_TOKEN.sub("[REDACTED_JWT]", text)
    text = _API_KEY_KV.sub(r"\1\2[REDACTED_SECRET]", text)
    text = _GENERIC_KEY_PATTERN.sub(r"\1[REDACTED_KEY]", text)
    return _LONG_DIGITS.sub("[REDACTED_DIGITS]", text)


class PrivacyLogFilter(logging.Filter):
    """Redact common PII in messages and exception tracebacks before handlers emit records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_log_text(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.exc_text = redact_log_text(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True
