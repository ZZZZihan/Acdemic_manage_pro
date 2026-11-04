"""One OpenAI-compatible chat client for DeepSeek, OpenAI, and Ollama.

Keys and prompts are never logged. Missing credentials return None so the
caller can refuse instead of inventing an answer.
"""
import codecs
import json
import os

import requests

_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 90


def provider_model(provider):
    name = (provider or "deepseek").strip().lower()
    if name == "openai":
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if name == "ollama":
        return os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
    return os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def complete(provider, messages):
    """Return text plus token counts, or None when the provider cannot be called."""
    spec = _spec(provider)
    if spec is None:
        return None
    url, headers, model = spec
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 800,
        "stream": False,
    }
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError):
        return None
    text = ""
    try:
        text = body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return None
    usage = body.get("usage") or {}
    return {
        "text": text,
        "model": model,
        "prompt_tokens": int(usage.get("prompt_tokens") or _estimate(messages)),
        "completion_tokens": int(usage.get("completion_tokens") or _estimate(text)),
    }


def stream(provider, messages):
    """Yield content deltas. Return None if the provider cannot be called.

    The iterator's ``usage`` dict is filled when the stream finishes.
    """
    spec = _spec(provider)
    if spec is None:
        return None
    url, headers, model = spec
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 800,
        "stream": True,
    }
    usage = {"model": model, "prompt_tokens": _estimate(messages), "completion_tokens": 0}

    class _TokenStream:
        def __init__(self):
            self.usage = usage
            self.model = model

        def __iter__(self):
            return _iterate()

    def _iterate():
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
                stream=True,
            )
            response.raise_for_status()
        except requests.RequestException:
            return
        pieces = []
        for raw in _sse_lines(response):
            if not raw:
                continue
            line = raw[5:].strip() if raw.startswith("data:") else raw.strip()
            if line == "[DONE]":
                break
            try:
                event = json.loads(line)
            except ValueError:
                continue
            choice = (event.get("choices") or [{}])[0]
            delta = (choice.get("delta") or {}).get("content")
            if delta is None and choice.get("message"):
                delta = choice["message"].get("content")
            if delta:
                pieces.append(delta)
                yield delta
            event_usage = event.get("usage") or {}
            if event_usage.get("prompt_tokens"):
                usage["prompt_tokens"] = int(event_usage["prompt_tokens"])
            if event_usage.get("completion_tokens"):
                usage["completion_tokens"] = int(event_usage["completion_tokens"])
        if not usage["completion_tokens"]:
            usage["completion_tokens"] = _estimate("".join(pieces))

    return _TokenStream()


def _spec(provider):
    name = (provider or "deepseek").strip().lower()
    model = provider_model(name)
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            return None
        url = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
        return url, _headers(key), model
    if name == "ollama":
        return _ollama_url(), {"Content-Type": "application/json"}, model
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        return None
    url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
    return url, _headers(key), model


def _sse_lines(response):
    """Buffer SSE by newline and keep UTF-8 characters whole across TCP chunks."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    pending = ""
    for chunk in response.iter_content(chunk_size=512):
        if not chunk:
            continue
        pending += decoder.decode(chunk)
        while "\n" in pending:
            line, pending = pending.split("\n", 1)
            yield line.rstrip("\r")
    pending += decoder.decode(b"", final=True)
    if pending:
        yield pending.rstrip("\r")


def _headers(key):
    return {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}


def _ollama_url():
    base = os.environ.get("OLLAMA_BASE_URL", "").strip()
    if base:
        return base.rstrip("/") + "/chat/completions"
    legacy = os.environ.get("OLLAMA_API_URL", "").strip()
    if legacy.endswith("/api/chat"):
        return legacy[: -len("/api/chat")] + "/v1/chat/completions"
    if legacy:
        return legacy
    return "http://127.0.0.1:11434/v1/chat/completions"


def _estimate(value):
    if isinstance(value, list):
        text = " ".join(str(item.get("content") or "") for item in value)
    else:
        text = str(value or "")
    return max(1, len(text) // 2) if text else 0
