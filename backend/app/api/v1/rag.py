from flask import current_app, jsonify, request

from app.api.v1.errors import bad_request
from app.audit import emit
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
from app.utils.chat_with_doc import _call_ai_api

rag_bp = __import__("flask").Blueprint("rag", __name__)


def _sources(hits):
    sources = []
    seen = set()
    for hit in hits:
        if hit["id"] in seen:
            continue
        seen.add(hit["id"])
        sources.append({
            "id": hit["id"],
            "title": hit.get("title") or "",
            "quote": hit.get("quote") or "",
            "source_url": hit.get("source_url"),
        })
    return sources


@rag_bp.route("/chat", methods=["POST"])
@rate_limit("chat")
@member_required
def rag_chat():
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return bad_request("缺少必要参数")
    provider = data.get("provider") or "deepseek"
    if not current_app.config.get("RAG_ENABLED"):
        emit("llm_call", outcome="unavailable", provider=provider, retrieved_doc_ids=[])
        return jsonify({
            "success": False,
            "code": "rag_unavailable",
            "message": RAG_UNAVAILABLE_MESSAGE,
        }), 503

    try:
        hits = retrieve(query, current_app.config.get("RAG_RETRIEVER", "vector"))
    except RagUnavailable as exc:
        emit("llm_call", outcome="unavailable", provider=provider, retrieved_doc_ids=[])
        return jsonify({
            "success": False,
            "code": "rag_unavailable",
            "message": str(exc) or RAG_UNAVAILABLE_MESSAGE,
        }), 503

    doc_ids = [hit["id"] for hit in hits]
    if not hits:
        emit("llm_call", outcome="no_grounded_answer", provider=provider, retrieved_doc_ids=[])
        return jsonify({
            "success": False,
            "code": "no_grounded_answer",
            "message": NO_GROUNDED_MESSAGE,
            "sources": [],
        })

    context = "\n\n".join(
        f"文档 {hit['id']}（{hit.get('title') or '未命名'}）: {hit.get('quote') or ''}"
        for hit in hits
    )
    system_prompt = (
        "你是实验室知识库问答助手。只根据给定文档回答。"
        "文档没有依据时直接说明不知道，不要编造。"
        "回答时引用文档 id。\n\n"
        f"{context}"
    )
    answer = _call_ai_api(query, system_prompt, provider)
    if not answer:
        emit(
            "llm_call",
            outcome="llm_unavailable",
            provider=provider,
            retrieved_doc_ids=doc_ids,
        )
        return jsonify({
            "success": False,
            "code": "llm_unavailable",
            "message": LLM_UNAVAILABLE_MESSAGE,
            "sources": _sources(hits),
        }), 503

    emit("llm_call", outcome="answered", provider=provider, retrieved_doc_ids=doc_ids)
    return jsonify({
        "success": True,
        "data": {
            "answer": answer,
            "sources": _sources(hits),
            "model": provider,
            "retrieved_docs": len(doc_ids),
        },
    })


@rag_bp.route("/init_flashrag", methods=["POST"])
@rate_limit("chat")
@admin_required
def init_flashrag():
    count = sync_corpus_from_db()
    from app.models import TechSummary

    rows = TechSummary.query.count()
    index_ready = False
    if current_app.config.get("RAG_ENABLED") and current_app.config.get("RAG_RETRIEVER") == "vector":
        try:
            from app.rag.service import _build_vector_index

            _build_vector_index()
            index_ready = True
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
    emit(
        "index_rebuild",
        outcome="ok",
        corpus_docs=count,
        tech_summary_rows=rows,
        index_ready=index_ready,
    )
    return jsonify({
        "success": True,
        "message": "语料已从数据库重建",
        "corpus_docs": count,
        "tech_summary_rows": rows,
        "index_ready": index_ready,
        "corpus_matches_rows": count == rows and count == corpus_count(),
    })
