"""Logging setup: human-readable in development, JSON lines in production.

Standard library only. Every record carries the current request id (see
``shared/http/request_id.py``) so that logs can be correlated with responses.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Literal

from cleanarch.shared.http.request_id import current_request_id

LogFormat = Literal["text", "json"]


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):  # ``extra={"request_id": ...}`` wins
            record.request_id = current_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", fmt: LogFormat = "text") -> None:
    """Install (or replace) the template's handler on the root logger.

    Only our own previous handler is removed: handlers installed by the host
    (pytest's capture, a process manager, an APM agent) are left alone.
    """
    handler = logging.StreamHandler(sys.stderr)
    handler.set_name("cleanarch")
    handler.addFilter(RequestIdFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s [%(request_id)s] %(name)s: %(message)s")
        )
    root = logging.getLogger()
    root.handlers[:] = [h for h in root.handlers if h.get_name() != "cleanarch"] + [handler]
    root.setLevel(level.upper())
    # uvicorn installs its own handlers; route them through ours for one consistent format.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
