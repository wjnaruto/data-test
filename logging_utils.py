import json
import logging
import ntpath
import sys
from datetime import datetime
from uuid import uuid4

from logs.context import request_id_ctx, correlation_id_ctx
from misc.config import settings


PROMOTED_FIELDS = (
    "client",
    "status",
    "remitter",
    "stage",
    "reason",
    "record_id",
    "path",
    "base_name",
    "md5",
    "error",
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        obj = {
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "severity": record.levelname,
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "message": record.getMessage(),
            "raw_message": getattr(record, "raw_message", None),
            "instance_id": getattr(record, "instance_id", None),
            "request_id": getattr(record, "request_id", None),
            "file_name": getattr(record, "file_name", None),
            "file_basename": ntpath.basename(getattr(record, "file_name", "") or "") or None,
            "correlation_id": getattr(record, "correlation_id", None),
        }
        for k in PROMOTED_FIELDS:
            v = getattr(record, k, None)
            if v is not None:
                obj[k] = v

        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        } | set(obj.keys())

        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in reserved and not k.startswith("_") and v is not None
        }
        if extra_fields:
            obj["fields"] = extra_fields

        return json.dumps({k: v for k, v in obj.items() if v is not None}, ensure_ascii=False)


def setup_json_logger() -> logging.Logger:
    logger = logging.getLogger("coordinator")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    logger.handlers.clear()
    logger.addHandler(handler)

    return logger


logger = setup_json_logger()


def _build_summary_message(event: str, *, file: str | None, message: str | None, extra: dict) -> str:
    parts = [event]
    if file:
        parts.append(f"file={file}")
    for k in ("remitter", "client", "status", "stage"):
        v = extra.get(k)
        if v:
            parts.append(f"{k}={v}")
    if message:
        parts.append(f"detail={message}")
    return " | ".join(parts)


def log_event(event: str, *, level: str = "info", file: str | None = None, message: str | None = None, **extra):
    record_extra = {
        "event": event,
        "file_name": file,
        "instance_id": settings.INSTANCE_ID,
        "request_id": request_id_ctx.get(),
        "correlation_id": correlation_id_ctx.get(),
        "raw_message": message,
    }
    record_extra.update(extra)
    msg = _build_summary_message(event, file=file, message=message, extra=record_extra)
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(msg, extra=record_extra)


def new_request_id() -> str:
    return "req-" + uuid4().hex[:10]


def new_correlation_id() -> str:
    return "corr-" + uuid4().hex[:8]
