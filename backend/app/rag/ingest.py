"""Index technical summaries and their uploaded attachments."""
import logging
from pathlib import Path

from app.rag.acl import can_read
from app.rag.chunk import chunk_document
from app.rag.engine import HashEmbedder, search_chunks
from app.rag.extract import extract_file
from app.rag.store import SqliteVectorStore

logger = logging.getLogger(__name__)

_STORES = {}


def get_store():
    from flask import current_app

    path = current_app.config.get("RAG_INDEX_PATH")
    store = _STORES.get(path)
    if store is None:
        store = SqliteVectorStore(path)
        _STORES[path] = store
    return store


def reset_stores():
    for store in _STORES.values():
        try:
            store.close()
        except Exception:
            pass
    _STORES.clear()


def active_embedder():
    """Hash by default. Neural weights load only when RAG is on and requested."""
    from flask import current_app

    name = (current_app.config.get("RAG_EMBEDDER") or "hash").strip().lower()
    enabled = bool(current_app.config.get("RAG_ENABLED"))
    if name in {"bge", "sentence-transformers", "neural"} and enabled:
        from app.rag.embed import NeuralEmbedder

        return NeuralEmbedder(current_app.config.get("RAG_EMBEDDING_MODEL"))
    return HashEmbedder()


def upsert_summary(summary):
    """Chunk one row and upsert it. Attachment failures are logged, not swallowed silently."""
    from flask import current_app

    store = get_store()
    body = summary.content or ""
    title = summary.title or ""
    chunks = _tag(chunk_document(body, title=title), "tech_summary")
    file_path = getattr(summary, "file_path", None) or ""
    if file_path:
        resolved = _resolve_upload(file_path, current_app.config.get("UPLOAD_FOLDER"))
        if resolved is None:
            store.log_ingest(summary.id, file_path, "unsupported_path", "outside upload root or missing")
        else:
            text, status = extract_file(resolved)
            if status != "ok":
                store.log_ingest(summary.id, resolved.name, status, status)
            else:
                attachment = _tag(chunk_document(text, title=title), "upload")
                for chunk in attachment:
                    chunk["section"] = ("附件 / " + chunk["section"]).strip(" /")
                chunks.extend(attachment)
    if not chunks and title:
        chunks = [{
            "section": title,
            "text": title,
            "span_start": 0,
            "span_end": 0,
            "source": "tech_summary",
        }]
    embedder = active_embedder()
    vectors = embedder.embed([chunk["text"] for chunk in chunks]) if chunks else []
    updated = summary.updated_at.isoformat() if getattr(summary, "updated_at", None) else ""
    store.upsert_document(
        {
            "doc_id": str(summary.id),
            "title": title,
            "source": "tech_summary",
            "source_url": summary.source_url or "",
            "updated_at": updated,
            "access_scope": getattr(summary, "access_scope", None) or "lab",
            "owner_id": summary.user_id,
            "status": "ok",
        },
        chunks,
        vectors,
    )
    return len(chunks)


def delete_summary(doc_id):
    get_store().delete_document(doc_id)


def rebuild_from_db():
    """Full rebuild from technical-summary rows. Returns counts, never a partial silent skip."""
    from app.models import TechSummary

    store = get_store()
    store.clear()
    rows = TechSummary.query.order_by(TechSummary.id.asc()).all()
    chunks = 0
    for row in rows:
        chunks += upsert_summary(row)
    return {
        "documents": store.document_count(),
        "chunks": chunks,
        "tech_summary_rows": len(rows),
        "failures": store.failure_count(),
    }


def search(query, user, mode, top_k=5):
    from flask import current_app

    store = get_store()
    if store.document_count() == 0 and _row_count():
        rebuild_from_db()
    visible = [
        chunk for chunk in store.iter_chunks()
        if can_read(chunk.get("access_scope"), chunk.get("owner_id"), user)
    ]
    threshold = float(current_app.config.get("RAG_SCORE_THRESHOLD", 0.12))
    embedder = active_embedder()
    rerank_kind = (current_app.config.get("RAG_RERANKER") or "overlap").strip().lower()
    result = search_chunks(
        visible,
        query,
        embedder,
        mode=mode,
        top_k=top_k,
        threshold=threshold,
    )
    if mode in {"hybrid_rerank", "vector", "dense", "hybrid"} and rerank_kind == "cross-encoder" and mode == "hybrid_rerank":
        result = _apply_cross_encoder(query, result, top_k, threshold)
    return result, getattr(embedder, "name", "hash")


def _apply_cross_encoder(query, result, top_k, threshold):
    from app.rag.embed import cross_encode
    from app.rag.engine import support_score

    pool = result["candidates"] or result["hits"]
    if not pool:
        return result
    scores = cross_encode(query, [hit.get("text") or "" for hit in pool])
    ranked = []
    for hit, score in zip(pool, scores):
        updated = dict(hit)
        updated["rerank_score"] = round(score, 4)
        updated["score"] = round(score, 4)
        ranked.append(updated)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    top = ranked[0]
    support = support_score(query, top.get("text") or "")
    refused = support < threshold
    return {
        "hits": [] if refused else ranked[:top_k],
        "candidates": ranked[:top_k],
        "refused": refused,
        "support": round(support, 4),
        "mode": "hybrid_rerank",
    }


def _row_count():
    from app.models import TechSummary

    return TechSummary.query.count()


def _tag(chunks, source):
    tagged = []
    for chunk in chunks:
        item = dict(chunk)
        item["source"] = source
        tagged.append(item)
    return tagged


def _resolve_upload(file_path, upload_root):
    if not file_path or not upload_root:
        return None
    root = Path(upload_root).resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate.name
    try:
        candidate = candidate.resolve()
    except OSError:
        return None
    if candidate != root and root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


def index_corpus_rows(rows, store, embedder):
    """Index plain dicts. Used by the offline eval script, outside Flask."""
    store.clear()
    for row in rows:
        chunks = _tag(chunk_document(row.get("content") or "", title=row.get("title") or ""), "tech_summary")
        if not chunks and row.get("title"):
            chunks = [{
                "section": row.get("title") or "",
                "text": row.get("title") or "",
                "span_start": 0,
                "span_end": 0,
                "source": "tech_summary",
            }]
        vectors = embedder.embed([chunk["text"] for chunk in chunks]) if chunks else []
        store.upsert_document(
            {
                "doc_id": str(row["doc_id"]),
                "title": row.get("title") or "",
                "source": row.get("source") or "seed",
                "source_url": row.get("source_url") or "",
                "updated_at": row.get("updated_at") or "",
                "access_scope": row.get("access_scope") or "lab",
                "owner_id": row.get("owner_id"),
                "status": "ok",
            },
            chunks,
            vectors,
        )
    return store.document_count()
