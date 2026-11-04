"""Deterministic tokenization, fusion, and hashing embedder.

This module imports nothing heavier than the standard library. Neural
embeddings and cross-encoders stay behind explicit calls in ``embed.py``.
"""
import hashlib
import math
import re
from collections import Counter

# Weighted sum of min-max normalized scores. Rank-only fusion (plain RRF)
# hides the IDF spike of a rare identifier, which is the signal Chinese
# technical notes actually need. These two weights are the only fusion knobs.
FUSION_BM25_WEIGHT = 0.62
FUSION_DENSE_WEIGHT = 0.38
HASH_DIM = 256

_IDENT = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.I)
_CJK = re.compile(r"[\u4e00-\u9fff]")
_STOP = set("的了是在和与或及对把被从以而也就都还很这那你我他她它吗呢吧啊不有为等中上下并及其或")


def tokenize(text):
    """Identifiers plus CJK bigrams. Function-character bigrams are dropped."""
    raw = text or ""
    lowered = raw.lower()
    idents = [token.lower() for token in _IDENT.findall(lowered)]
    chars = _CJK.findall(raw)
    bigrams = []
    for left, right in zip(chars, chars[1:]):
        if left in _STOP and right in _STOP:
            continue
        bigrams.append(left + right)
    return idents + bigrams


def _minmax(values):
    if not values:
        return []
    low = min(values)
    high = max(values)
    if high <= low:
        return [0.0 if high <= 0 else 1.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def bm25_scores(query_tokens, docs_tokens, k1=1.5, b=0.75):
    """Okapi BM25. Empty documents score 0."""
    total = len(docs_tokens)
    if total == 0:
        return []
    df = Counter()
    for tokens in docs_tokens:
        df.update(set(tokens))
    lengths = [len(tokens) for tokens in docs_tokens]
    avgdl = sum(lengths) / total if total else 0.0
    query_counts = Counter(query_tokens)
    scores = []
    for tokens, length in zip(docs_tokens, lengths):
        if not tokens or not avgdl:
            scores.append(0.0)
            continue
        tf = Counter(tokens)
        score = 0.0
        for term, _qf in query_counts.items():
            freq = tf.get(term)
            if not freq:
                continue
            n = df.get(term, 0)
            idf = math.log(1.0 + (total - n + 0.5) / (n + 0.5))
            denom = freq + k1 * (1.0 - b + b * length / avgdl)
            score += idf * (freq * (k1 + 1.0)) / denom
        scores.append(score)
    return scores


class HashEmbedder:
    """Signed hashing trick over the same tokens BM25 uses. L2-normalized."""

    name = "hash"
    dim = HASH_DIM

    def embed(self, texts):
        return [_hash_vector(text, self.dim) for text in texts]


def _hash_vector(text, dim):
    vector = [0.0] * dim
    counts = Counter(tokenize(text))
    if not counts:
        return vector
    for token, count in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _dot(left, right):
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    return sum(left[i] * right[i] for i in range(size))


def support_score(query, text):
    """Fraction of distinct query tokens that appear in ``text``."""
    query_tokens = set(tokenize(query))
    if not query_tokens:
        return 0.0
    doc_tokens = set(tokenize(text))
    return len(query_tokens & doc_tokens) / len(query_tokens)


def rerank_overlap(query, hits):
    """Lexical rerank. Identifiers outweigh generic bigram overlap."""
    idents = [token.lower() for token in _IDENT.findall((query or "").lower())]
    ranked = []
    for hit in hits:
        text = hit.get("text") or ""
        coverage = support_score(query, text)
        if idents:
            found = sum(1 for token in idents if token in text.lower()) / len(idents)
        else:
            found = coverage
        score = 0.45 * coverage + 0.55 * found
        updated = dict(hit)
        updated["rerank_score"] = round(score, 4)
        updated["score"] = round(score, 4)
        ranked.append(updated)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def search_chunks(chunks, query, embedder, mode="hybrid", top_k=5, threshold=0.12, rerank_pool=15, evidence="support"):
    """Rank ``chunks`` and optionally refuse.

    ``evidence`` selects the number compared with ``threshold``:
    ``support`` (lexical overlap, the hash/CI default), ``dense`` (cosine of
    the top hit), or ``score`` (the ranking score after fusion or rerank).
    ``threshold=None`` keeps every hit.
    """
    mode = (mode or "hybrid").lower()
    if mode == "vector":
        mode = "dense"
    if mode not in {"dense", "hybrid", "hybrid_rerank"}:
        raise ValueError(f"unknown retrieval mode: {mode}")

    if not chunks or not (query or "").strip():
        return {"hits": [], "candidates": [], "refused": True, "support": 0.0, "mode": mode}

    query_tokens = tokenize(query)
    doc_tokens = [tokenize(chunk.get("text") or "") for chunk in chunks]
    sparse = bm25_scores(query_tokens, doc_tokens) if mode != "dense" else [0.0] * len(chunks)
    if hasattr(embedder, "embed_query"):
        query_vector = embedder.embed_query(query)
    else:
        query_vector = embedder.embed([query])[0]
    dense = [_dot(query_vector, chunk.get("vector") or []) for chunk in chunks]

    if mode == "dense":
        combined = dense
    else:
        norm_sparse = _minmax(sparse)
        norm_dense = _minmax(dense)
        combined = [
            FUSION_BM25_WEIGHT * left + FUSION_DENSE_WEIGHT * right
            for left, right in zip(norm_sparse, norm_dense)
        ]

    order = sorted(range(len(chunks)), key=lambda index: combined[index], reverse=True)
    ranked = []
    for index in order:
        hit = dict(chunks[index])
        hit["dense_score"] = round(float(dense[index]), 4)
        hit["bm25_score"] = round(float(sparse[index]), 4)
        hit["score"] = round(float(combined[index]), 4)
        hit.pop("vector", None)
        ranked.append(hit)

    if mode == "hybrid_rerank":
        pool = ranked[: max(rerank_pool, top_k)]
        tail = ranked[len(pool):]
        ranked = rerank_overlap(query, pool) + tail

    candidates = ranked[:top_k]
    top = candidates[0] if candidates else None
    support = support_score(query, top.get("text") or "") if top else 0.0
    if top is None:
        evidence_value = 0.0
    elif evidence == "support":
        evidence_value = support
    elif evidence == "dense":
        evidence_value = float(top.get("dense_score") or 0.0)
    elif evidence == "score":
        evidence_value = float(top.get("score") or 0.0)
    else:
        raise ValueError(f"unknown evidence: {evidence}")
    refused = False if threshold is None else evidence_value < threshold
    hits = [] if refused else candidates
    return {
        "hits": hits,
        "candidates": candidates,
        "refused": refused,
        "support": round(support, 4),
        "evidence": round(evidence_value, 4),
        "mode": mode,
    }
