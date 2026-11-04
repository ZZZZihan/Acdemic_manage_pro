"""Corpus sync and retrieval.

Importing this module does not download or load an embedding model.
Keyword search stays a substring match so the compliance smoke tests can run
without building vectors. ``vector``, ``hybrid``, and ``hybrid_rerank`` read
the persistent SQLite index.
"""
import logging
import time

from flask import g, has_request_context

from app.rag.errors import RagUnavailable

logger = logging.getLogger(__name__)

NO_GROUNDED_MESSAGE = "知识库中没有足够依据回答该问题。"
RAG_UNAVAILABLE_MESSAGE = "检索服务未启用。"
LLM_UNAVAILABLE_MESSAGE = "语言模型未配置或调用失败，已拒绝生成无依据回答。"

__all__ = [
    "NO_GROUNDED_MESSAGE",
    "RAG_UNAVAILABLE_MESSAGE",
    "LLM_UNAVAILABLE_MESSAGE",
    "RagUnavailable",
    "sync_corpus_from_db",
    "corpus_count",
    "keyword_retrieve",
    "retrieve",
    "reset_for_tests",
]


def sync_corpus_from_db():
    """Replace the in-memory corpus with every technical summary row."""
    from app.models import TechSummary
    from app.utils.knowledge_base import knowledge_base

    documents = {}
    rows = TechSummary.query.order_by(TechSummary.id.asc()).all()
    for row in rows:
        documents[str(row.id)] = {
            "title": row.title or "",
            "content": row.content or "",
            "metadata": {
                "summary_type": row.summary_type,
                "tags": row.tags,
                "source_url": row.source_url,
                "user_id": row.user_id,
                "access_scope": getattr(row, "access_scope", None) or "lab",
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            },
        }
    knowledge_base.replace_all(documents)
    return len(documents)


def corpus_count():
    from app.utils.knowledge_base import knowledge_base

    return len(knowledge_base.documents)


def keyword_retrieve(query, top_k=4, user=None):
    from app.rag.acl import can_read
    from app.utils.knowledge_base import knowledge_base

    needle = (query or "").strip().lower()
    if len(needle) < 2:
        return []
    hits = []
    for doc_id, doc in knowledge_base.documents.items():
        metadata = doc.get("metadata") or {}
        if not can_read(metadata.get("access_scope"), metadata.get("user_id"), user):
            continue
        title = doc.get("title") or ""
        content = doc.get("content") or ""
        haystack = f"{title}\n{content}".lower()
        if needle not in haystack:
            continue
        quote = _quote(content, needle)
        hits.append({
            "id": doc_id,
            "doc_id": doc_id,
            "title": title,
            "quote": quote,
            "text": quote,
            "section": "",
            "span": None,
            "source": "tech_summary",
            "source_url": metadata.get("source_url"),
            "score": 1.0,
        })
        if len(hits) >= top_k:
            break
    return hits


def _quote(content, needle):
    lowered = content.lower()
    index = lowered.find(needle.lower())
    if index < 0:
        return content[:240]
    start = max(0, index - 40)
    end = min(len(content), index + len(needle) + 160)
    return content[start:end]


def retrieve(query, retriever, user=None):
    """Return citation hits. Weak hybrid evidence comes back as an empty list."""
    started = time.perf_counter()
    mode = (retriever or "hybrid").strip().lower()
    embedder_name = "none"
    refused = False
    support = None
    candidates = []
    try:
        if mode == "keyword":
            sync_corpus_from_db()
            hits = keyword_retrieve(query, user=user)
        elif mode in {"vector", "dense", "hybrid", "hybrid_rerank"}:
            from app.rag.ingest import search

            result, embedder_name = search(query, user, mode)
            hits = [_public_hit(hit) for hit in result["hits"]]
            candidates = [_public_hit(hit) for hit in result["candidates"]]
            refused = bool(result["refused"])
            support = result.get("support")
        else:
            raise RagUnavailable("未知检索器，检索服务不可用")
    except RagUnavailable:
        _remember_trace(started, mode, embedder_name, [], [], refused=True, support=None)
        raise
    chosen = candidates or hits
    _remember_trace(
        started,
        mode,
        embedder_name,
        hits,
        chosen,
        refused=refused or not hits,
        support=support,
    )
    return hits


def _public_hit(hit):
    text = hit.get("text") or ""
    return {
        "id": str(hit.get("doc_id") or hit.get("id")),
        "doc_id": str(hit.get("doc_id") or hit.get("id")),
        "title": hit.get("title") or "",
        "section": hit.get("section") or "",
        "span": hit.get("span"),
        "quote": text[:800],
        "text": text,
        "source": hit.get("source") or "tech_summary",
        "source_url": hit.get("source_url") or None,
        "score": hit.get("score"),
        "dense_score": hit.get("dense_score"),
        "bm25_score": hit.get("bm25_score"),
        "updated_at": hit.get("updated_at"),
        "access_scope": hit.get("access_scope") or "lab",
    }


def _remember_trace(started, mode, embedder_name, hits, candidates, refused, support):
    trace = {
        "retriever": mode,
        "embedder": embedder_name,
        "retrieval_ms": round((time.perf_counter() - started) * 1000, 2),
        "hit_ids": [hit["id"] for hit in hits],
        "candidate_ids": [hit["id"] for hit in candidates],
        "scores": [hit.get("score") for hit in candidates],
        "refused": refused,
        "support": support,
    }
    if has_request_context():
        g.rag_trace = trace


def reset_for_tests():
    from app.rag.ingest import reset_stores

    reset_stores()
