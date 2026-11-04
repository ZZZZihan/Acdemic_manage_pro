import json

from flask import Response, current_app, g, jsonify, request, stream_with_context

from app.api.v1.errors import bad_request
from app.audit import emit
from app.rag.generate import messages_for
from app.rag.llm import complete, stream
from app.rag.service import (
    LLM_UNAVAILABLE_MESSAGE,
    NO_GROUNDED_MESSAGE,
    RAG_UNAVAILABLE_MESSAGE,
    RagUnavailable,
    corpus_count,
    retrieve,
    sync_corpus_from_db,
)
from app.rate_limit import rate_limit
from app.security import admin_required, member_required

rag_bp = __import__("flask").Blueprint("rag", __name__)


def _sources(hits):
    sources = []
    seen = set()
    for hit in hits:
        doc_id = str(hit.get("doc_id") or hit.get("id"))
        if doc_id in seen:
            continue
        seen.add(doc_id)
        sources.append({
            "id": doc_id,
            "doc_id": doc_id,
            "title": hit.get("title") or "",
            "section": hit.get("section") or "",
            "span": hit.get("span"),
            "quote": hit.get("quote") or "",
            "source": hit.get("source") or "tech_summary",
            "source_url": hit.get("source_url"),
            "score": hit.get("score"),
        })
    return sources


def _trace_fields(extra=None):
    trace = dict(getattr(g, "rag_trace", {}) or {})
    fields = {
        "retriever": trace.get("retriever"),
        "embedder": trace.get("embedder"),
        "retrieval_ms": trace.get("retrieval_ms"),
        "hit_ids": trace.get("hit_ids") or [],
        "scores": trace.get("scores") or [],
        "support": trace.get("support"),
    }
    if extra:
        fields.update(extra)
    return fields


def _emit_trace(outcome, provider, model=None, prompt_tokens=0, completion_tokens=0):
    emit(
        "rag_trace",
        outcome=outcome,
        provider=provider,
        model=model or provider,
        prompt_tokens=int(prompt_tokens or 0),
        completion_tokens=int(completion_tokens or 0),
        **_trace_fields(),
    )


def _disabled(provider):
    _emit_trace("unavailable", provider)
    return jsonify({
        "success": False,
        "code": "rag_unavailable",
        "message": RAG_UNAVAILABLE_MESSAGE,
    }), 503


def _retrieve_or_response(query, provider):
    if not current_app.config.get("RAG_ENABLED"):
        return _disabled(provider)
    try:
        hits = retrieve(query, current_app.config.get("RAG_RETRIEVER", "hybrid"), user=getattr(g, "actor", None))
    except RagUnavailable as exc:
        _emit_trace("unavailable", provider)
        return jsonify({
            "success": False,
            "code": "rag_unavailable",
            "message": str(exc) or RAG_UNAVAILABLE_MESSAGE,
        }), 503
    if not hits:
        _emit_trace("no_grounded_answer", provider, prompt_tokens=0, completion_tokens=0)
        return jsonify({
            "success": False,
            "code": "no_grounded_answer",
            "message": NO_GROUNDED_MESSAGE,
            "sources": [],
        })
    return hits


@rag_bp.route("/chat", methods=["POST"])
@rate_limit("chat")
@member_required
def rag_chat():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return bad_request("缺少必要参数")
    provider = data.get("provider") or "deepseek"
    prepared = _retrieve_or_response(query, provider)
    if not isinstance(prepared, list):
        return prepared
    hits = prepared
    generated = complete(provider, messages_for(query, hits))
    if not generated or not (generated.get("text") or "").strip():
        _emit_trace("llm_unavailable", provider, prompt_tokens=0, completion_tokens=0)
        return jsonify({
            "success": False,
            "code": "llm_unavailable",
            "message": LLM_UNAVAILABLE_MESSAGE,
            "sources": _sources(hits),
        }), 503
    _emit_trace(
        "answered",
        provider,
        model=generated.get("model"),
        prompt_tokens=generated.get("prompt_tokens"),
        completion_tokens=generated.get("completion_tokens"),
    )
    return jsonify({
        "success": True,
        "data": {
            "answer": generated["text"],
            "sources": _sources(hits),
            "model": generated.get("model") or provider,
            "retrieved_docs": len(_sources(hits)),
        },
    })


@rag_bp.route("/chat/stream", methods=["POST"])
@rate_limit("chat")
@member_required
def rag_chat_stream():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return bad_request("缺少必要参数")
    provider = data.get("provider") or "deepseek"
    prepared = _retrieve_or_response(query, provider)
    if not isinstance(prepared, list):
        return prepared
    hits = prepared
    iterator = stream(provider, messages_for(query, hits))
    if iterator is None:
        _emit_trace("llm_unavailable", provider, prompt_tokens=0, completion_tokens=0)
        return jsonify({
            "success": False,
            "code": "llm_unavailable",
            "message": LLM_UNAVAILABLE_MESSAGE,
            "sources": _sources(hits),
        }), 503

    def generate():
        yield _sse("citations", {"sources": _sources(hits), "model": getattr(iterator, "model", provider)})
        produced = False
        for delta in iterator:
            if not delta:
                continue
            produced = True
            yield _sse("token", {"text": delta})
        usage = getattr(iterator, "usage", {}) or {}
        if not produced:
            _emit_trace("llm_unavailable", provider, model=usage.get("model"), prompt_tokens=0, completion_tokens=0)
            yield _sse("error", {"code": "llm_unavailable", "message": LLM_UNAVAILABLE_MESSAGE})
            return
        _emit_trace(
            "answered",
            provider,
            model=usage.get("model") or getattr(iterator, "model", provider),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
        yield _sse("done", {"outcome": "answered"})

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event, payload):
    body = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {body}\n\n"


@rag_bp.route("/init_flashrag", methods=["POST"])
@rate_limit("chat")
@admin_required
def init_flashrag():
    from app.models import TechSummary
    from app.rag.ingest import rebuild_from_db

    count = sync_corpus_from_db()
    rows = TechSummary.query.count()
    try:
        stats = rebuild_from_db()
    except RagUnavailable as exc:
        emit("index_rebuild", outcome="failed", corpus_docs=count, tech_summary_rows=rows)
        return jsonify({
            "success": False,
            "code": "rag_unavailable",
            "message": str(exc),
            "corpus_docs": count,
            "tech_summary_rows": rows,
            "index_ready": False,
        }), 503
    index_ready = stats["documents"] == rows
    emit(
        "index_rebuild",
        outcome="ok",
        corpus_docs=count,
        tech_summary_rows=rows,
        index_ready=index_ready,
        chunks=stats["chunks"],
        ingest_failures=stats["failures"],
    )
    return jsonify({
        "success": True,
        "message": "语料已从数据库重建",
        "corpus_docs": count,
        "tech_summary_rows": rows,
        "index_ready": index_ready,
        "chunks": stats["chunks"],
        "ingest_failures": stats["failures"],
        "corpus_matches_rows": count == rows and count == corpus_count() and stats["documents"] == rows,
    })
