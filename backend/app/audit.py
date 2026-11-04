"""Structured audit events.

Records are JSON objects. They identify the actor by numeric id, never by
email, and they never include secrets, prompts, document text, or tokens.
"""
import json
import logging
from datetime import datetime, timezone

from flask import current_app, g, has_request_context, request

_SECRET_KEYS = {
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "jwt",
    "email",
    "prompt",
    "content",
    "query",
}

logger = logging.getLogger("audit")


def _scrub(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                continue
            cleaned[key] = _scrub(item)
        return cleaned
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def emit(event, **fields):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor_id": fields.pop("actor_id", None),
        "endpoint": None,
        "method": None,
        "outcome": fields.pop("outcome", None),
    }
    if has_request_context():
        record["endpoint"] = request.path
        record["method"] = request.method
        record["request_id"] = getattr(g, "request_id", None)
        if record["actor_id"] is None and getattr(g, "actor", None) is not None:
            record["actor_id"] = g.actor.id
    record.update(_scrub(fields))
    line = json.dumps(record, ensure_ascii=False, default=str)
    logger.info(line)
    if has_request_context():
        buffer = current_app.config.get("AUDIT_EVENTS")
        if isinstance(buffer, list):
            buffer.append(record)
    return record
