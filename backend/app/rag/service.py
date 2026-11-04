"""Corpus sync and retrieval.

Importing this module does not download or load an embedding model.
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

NO_GROUNDED_MESSAGE = "知识库中没有足够依据回答该问题。"
RAG_UNAVAILABLE_MESSAGE = "检索服务未启用。"
LLM_UNAVAILABLE_MESSAGE = "语言模型未配置或调用失败，已拒绝生成无依据回答。"

_model = None
_index = None
_index_rows = None


class RagUnavailable(RuntimeError):
    pass


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
            },
        }
    knowledge_base.replace_all(documents)
    global _index, _index_rows
    _index = None
    _index_rows = None
    return len(documents)


def corpus_count():
    from app.utils.knowledge_base import knowledge_base

    return len(knowledge_base.documents)


def chunk_text(title, content, size=500, overlap=80):
    text = f"{title}\n\n{content}".strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    pieces = re.split(r"(?<=[。！？!?])|(?<=\.)\s+", text)
    chunks = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > size:
            if current:
                chunks.append(current)
                current = ""
            step = max(size - overlap, 1)
            for start in range(0, len(piece), step):
                chunks.append(piece[start:start + size])
            continue
        if current and len(current) + len(piece) + 1 > size:
            chunks.append(current)
            current = piece
        else:
            current = f"{current}{piece}" if not current else f"{current}{piece}"
    if current:
        chunks.append(current)
    return chunks or [text[:size]]


def keyword_retrieve(query, top_k=4):
    from app.utils.knowledge_base import knowledge_base

    needle = (query or "").strip().lower()
    if len(needle) < 2:
        return []
    hits = []
    for doc_id, doc in knowledge_base.documents.items():
        title = doc.get("title") or ""
        content = doc.get("content") or ""
        haystack = f"{title}\n{content}".lower()
        if needle not in haystack:
            continue
        metadata = doc.get("metadata") or {}
        hits.append({
            "id": doc_id,
            "title": title,
            "quote": _quote(content, needle),
            "source_url": metadata.get("source_url"),
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


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RagUnavailable("嵌入依赖未安装，检索服务不可用") from exc
    model_name = os.environ.get(
        "RAG_EMBEDDING_MODEL",
        "paraphrase-multilingual-MiniLM-L12-v2",
    )
    try:
        _model = SentenceTransformer(model_name)
    except Exception as exc:
        raise RagUnavailable("嵌入模型加载失败，检索服务不可用") from exc
    logger.info("embedding model loaded")
    return _model


def _build_vector_index():
    global _index, _index_rows
    from app.utils.knowledge_base import knowledge_base

    try:
        import faiss
        import numpy as np
    except ImportError as exc:
        raise RagUnavailable("向量索引依赖未安装，检索服务不可用") from exc

    model = _load_model()
    rows = []
    texts = []
    for doc_id, doc in knowledge_base.documents.items():
        metadata = doc.get("metadata") or {}
        for chunk in chunk_text(doc.get("title") or "", doc.get("content") or ""):
            rows.append({
                "id": doc_id,
                "title": doc.get("title") or "",
                "quote": chunk[:240],
                "source_url": metadata.get("source_url"),
            })
            texts.append(chunk)
    if not texts:
        _index = None
        _index_rows = []
        return _index
    embeddings = model.encode(texts, normalize_embeddings=True)
    matrix = np.asarray(embeddings, dtype="float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    _index = index
    _index_rows = rows
    return _index


def vector_retrieve(query, top_k=4):
    if not (query or "").strip():
        return []
    if _index is None:
        _build_vector_index()
    if _index is None or not _index_rows:
        return []
    model = _load_model()
    import numpy as np

    query_vector = model.encode([query], normalize_embeddings=True)
    query_vector = np.asarray(query_vector, dtype="float32")
    scores, indices = _index.search(query_vector, min(top_k, len(_index_rows)))
    hits = []
    seen = set()
    for score, row_index in zip(scores[0], indices[0]):
        if row_index < 0 or float(score) < 0.35:
            continue
        row = _index_rows[int(row_index)]
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        hit = dict(row)
        hit["score"] = round(float(score), 4)
        hits.append(hit)
    return hits


def retrieve(query, retriever):
    sync_corpus_from_db()
    if retriever == "keyword":
        return keyword_retrieve(query)
    if retriever == "vector":
        return vector_retrieve(query)
    raise RagUnavailable("未知检索器，检索服务不可用")


def reset_for_tests():
    global _model, _index, _index_rows
    _model = None
    _index = None
    _index_rows = None
