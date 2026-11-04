"""In-process fixed-window rate limiter.

One worker only. Put a shared store in front of this process before running
more than one web worker; the limit is documented in SECURITY.md.
"""
import threading
import time
from functools import wraps

from flask import current_app, jsonify, request

from app.audit import emit

_lock = threading.Lock()
_buckets = {}


def reset_rate_limits():
    with _lock:
        _buckets.clear()


def _allow(key, limit, window):
    now = time.monotonic()
    with _lock:
        recent = [stamp for stamp in _buckets.get(key, []) if now - stamp < window]
        if len(recent) >= limit:
            _buckets[key] = recent
            return False
        recent.append(now)
        _buckets[key] = recent
        return True


def rate_limit(group):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if group == "auth":
                limit = current_app.config["AUTH_RATE_LIMIT"]
                window = current_app.config["AUTH_RATE_WINDOW_SECONDS"]
            else:
                limit = current_app.config["CHAT_RATE_LIMIT"]
                window = current_app.config["CHAT_RATE_WINDOW_SECONDS"]
            identity = request.remote_addr or "unknown"
            if not _allow(f"{group}:{identity}", limit, window):
                emit("rate_limited", outcome="denied", rate_group=group)
                return jsonify({
                    "success": False,
                    "code": "rate_limited",
                    "message": "请求过于频繁，请稍后再试",
                }), 429
            return fn(*args, **kwargs)

        return wrapper

    return decorator
