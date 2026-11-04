"""p1-v2 retrieval eval.

Hash mode does not import sentence-transformers. The bge mode is manual:
it reads cached weights and refuses to download (HF_HUB_OFFLINE=1).

From the backend directory::

    python -m evals.run_v2 --embedder hash --write
    python -m evals.run_v2 --embedder bge --write

Reported metrics are the held-out ``test`` split. Dense cosine and
cross-encoder thresholds are chosen on ``dev`` only.
"""
import argparse
import json
import math
import os
import tempfile
import time

from app.rag.engine import HashEmbedder
from app.rag.ingest import index_corpus_rows
from app.rag.store import SqliteVectorStore
from evals.run_eval import load_jsonl


HASH_THRESHOLD = 0.12
POOL = 15
TOP_K = 5
COSINE_GRID = [round(0.20 + index * 0.02, 2) for index in range(33)]


def evaluate_hash(documents, questions, top_k=TOP_K):
    """Hash dense + hash hybrid on whatever questions are passed in.

    Callers that want the held-out numbers pass the test split. Threshold
    stays at the lexical 0.12 used by p1-v1; it is not retuned.
    """
    chunks, embedder = _index(documents, HashEmbedder())
    modes = {}
    for mode in ("dense", "hybrid"):
        rows = _collect(chunks, questions, embedder, mode=mode, pool=top_k, cross=False)
        scored = _score(rows, "support", HASH_THRESHOLD, split=None)
        modes[mode] = _public_metrics(scored, HASH_THRESHOLD, "support")
    by_type = {
        mode: _type_breakdown(
            _collect(chunks, questions, embedder, mode=mode, pool=top_k, cross=False),
            "support",
            HASH_THRESHOLD,
        )
        for mode in ("dense", "hybrid")
    }
    return {
        "set_version": "p1-v2",
        "split": _split_label(questions),
        "embedder": "hash",
        "device": "cpu",
        "threshold_policy": "fixed lexical support 0.12; not tuned on p1-v2",
        "answerable": sum(1 for item in questions if item["answerable"]),
        "unanswerable": sum(1 for item in questions if not item["answerable"]),
        "top_k": top_k,
        "modes": modes,
        "by_type": by_type,
        "notes": (
            "Hash embedder plus BM25. Refusal uses lexical support, not cosine. "
            "Latency is retrieval only, after the index is built, on this machine."
        ),
    }


def evaluate_bge(documents, questions, top_k=TOP_K):
    """Tune bge thresholds on dev, score the test split once."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("RAG_DEVICE", "cpu")
    from app.rag.embed import NeuralEmbedder, cross_encode

    dev = [item for item in questions if item.get("split") == "dev"]
    test = [item for item in questions if item.get("split") == "test"]
    if not dev or not test:
        raise SystemExit("p1-v2 questions need both dev and test splits")
    embedder = NeuralEmbedder(os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"))
    chunks, embedder = _index(documents, embedder)
    embedder.embed_query("预热")
    cross_encode("预热", ["预热文本"])

    dense_rows = _collect(chunks, questions, embedder, mode="dense", pool=top_k, cross=False)
    hybrid_rows = _collect(chunks, questions, embedder, mode="hybrid", pool=POOL, cross=False)
    cross_rows = _with_cross(hybrid_rows)

    dense_choice = _tune(dense_rows, "dense", COSINE_GRID)
    hybrid_choice = _tune(hybrid_rows, "dense", COSINE_GRID)
    cross_choice = _tune(cross_rows, "cross", _cross_grid(cross_rows))

    modes = {
        "dense": _public_metrics(_score(dense_rows, "dense", dense_choice["threshold"], "test"), dense_choice["threshold"], "dense"),
        "hybrid": _public_metrics(_score(hybrid_rows, "dense", hybrid_choice["threshold"], "test"), hybrid_choice["threshold"], "dense"),
        "hybrid_cross_encoder": _public_metrics(
            _score(cross_rows, "cross", cross_choice["threshold"], "test"),
            cross_choice["threshold"],
            "cross",
        ),
    }
    return {
        "set_version": "p1-v2",
        "split": "test",
        "embedder": "bge",
        "device": "cpu",
        "embedding_model": embedder.model_name,
        "rerank_model": os.environ.get("RAG_RERANK_MODEL", "BAAI/bge-reranker-base"),
        "query_prefix": NeuralEmbedder.QUERY_PREFIX,
        "library_versions": _versions(),
        "threshold_policy": (
            "Cosine and cross-encoder thresholds maximize "
            "0.5*answerable_accept + 0.5*unanswerable_refuse on the dev split. "
            "Test rows are scored once with the chosen threshold."
        ),
        "answerable": sum(1 for item in test if item["answerable"]),
        "unanswerable": sum(1 for item in test if not item["answerable"]),
        "dev_questions": len(dev),
        "test_questions": len(test),
        "top_k": top_k,
        "rerank_pool": POOL,
        "modes": modes,
        "tuning": {
            "split": "dev",
            "objective": "0.5 * answerable_accept_rate + 0.5 * unanswerable_refuse_rate",
            "tie_break": ["citation_accuracy", "recall_at_5", "higher_threshold"],
            "dense": _tuning_record(dense_choice, "cosine 0.20..0.84 step 0.02", dense_rows, "dense"),
            "hybrid": _tuning_record(hybrid_choice, "cosine 0.20..0.84 step 0.02", hybrid_rows, "dense"),
            "hybrid_cross_encoder": _tuning_record(
                cross_choice,
                "midpoints of dev top-hit cross-encoder scores, plus always-accept and always-refuse",
                cross_rows,
                "cross",
            ),
        },
        "by_type": {
            "dense": _type_breakdown(dense_rows, "dense", dense_choice["threshold"]),
            "hybrid": _type_breakdown(hybrid_rows, "dense", hybrid_choice["threshold"]),
            "hybrid_cross_encoder": _type_breakdown(cross_rows, "cross", cross_choice["threshold"]),
        },
        "notes": (
            "bge hybrid refuses on the fused top hit's dense cosine, not the min-max fusion score. "
            "hybrid_cross_encoder retrieves a hybrid pool of 15, reranks with the cross-encoder, "
            "and refuses on that score. sentence-transformers applies sigmoid for this one-label "
            "reranker, so the score is on (0, 1), not a raw logit. Latency is per test query after "
            "weights are loaded; index time is excluded. CI does not run this path."
        ),
    }


def render(report):
    lines = [
        f"set={report.get('set_version')} split={report.get('split')} embedder={report.get('embedder')} "
        f"answerable={report.get('answerable')} unanswerable={report.get('unanswerable')}",
        f"{'mode':<24} {'Recall@5':>10} {'MRR':>10} {'citation':>10} {'refusal':>10} {'thr':>8} {'p50ms':>8} {'p95ms':>8}",
    ]
    for mode, metrics in report["modes"].items():
        latency = metrics.get("latency_ms") or {}
        lines.append(
            f"{mode:<24} {metrics['recall_at_5']:>10.4f} {metrics['mrr']:>10.4f} "
            f"{metrics['citation_accuracy']:>10.4f} {metrics['refusal_correctness']:>10.4f} "
            f"{metrics['threshold']:>8.4f} {latency.get('p50', 0):>8.1f} {latency.get('p95', 0):>8.1f}"
        )
    tuning = report.get("tuning") or {}
    for name, record in tuning.items():
        if not isinstance(record, dict) or "chosen_threshold" not in record:
            continue
        dev = record["dev"]
        lines.append(
            f"dev {name}: threshold={record['chosen_threshold']:.4f} "
            f"objective={dev['objective']:.4f} accept={dev['answerable_accept_rate']:.4f} "
            f"refuse={dev['unanswerable_refuse_rate']:.4f} "
            f"score=[{record['dev_score_min']:.4f}, {record['dev_score_max']:.4f}]"
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedder", choices=("hash", "bge"), default="hash")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.dirname(__file__)
    documents = load_jsonl(os.path.join(root, "corpus_v2.jsonl"))
    questions = load_jsonl(os.path.join(root, "questions_v2.jsonl"))
    if args.embedder == "hash":
        test = [item for item in questions if item.get("split") == "test"]
        report = evaluate_hash(documents, test)
        filename = "baseline_p1v2_hash.json"
    else:
        report = evaluate_bge(documents, questions)
        filename = "baseline_p1v2_bge.json"
    print(render(report))
    if args.write:
        path = os.path.join(root, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"wrote {path}")
    return report


def _index(documents, embedder):
    directory = tempfile.mkdtemp(prefix="rag-eval-v2-")
    path = os.path.join(directory, "index.sqlite")
    store = SqliteVectorStore(path)
    index_corpus_rows(documents, store, embedder)
    chunks = list(store.iter_chunks())
    store.close()
    return chunks, embedder


def _collect(chunks, questions, embedder, mode, pool, cross):
    from app.rag.engine import search_chunks

    rows = []
    for item in questions:
        started = time.perf_counter()
        result = search_chunks(
            chunks,
            item["question"],
            embedder,
            mode=mode,
            top_k=pool,
            threshold=None,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        candidates = result["candidates"]
        top = candidates[0] if candidates else None
        rows.append({
            "split": item.get("split"),
            "answerable": bool(item["answerable"]),
            "doc_id": item.get("doc_id"),
            "key_phrase": item.get("key_phrase") or "",
            "type": item.get("type"),
            "latency_ms": latency_ms,
            "support": float(result.get("support") or 0.0),
            "dense": float(top.get("dense_score") or 0.0) if top else 0.0,
            "cross": None,
            "_question": item["question"],
            "hits": [
                {"doc_id": hit.get("doc_id"), "text": hit.get("text") or ""}
                for hit in candidates[:TOP_K]
            ],
            "_pool": candidates,
        })
    return rows


def _with_cross(rows):
    from app.rag.embed import cross_encode

    scored = []
    for row in rows:
        pool = row.get("_pool") or []
        started = time.perf_counter()
        if pool:
            logits = cross_encode(row["_question"], [hit.get("text") or "" for hit in pool])
            order = sorted(range(len(pool)), key=lambda index: logits[index], reverse=True)
            hits = [
                {"doc_id": pool[index].get("doc_id"), "text": pool[index].get("text") or ""}
                for index in order[:TOP_K]
            ]
            top_logit = float(logits[order[0]])
        else:
            hits = []
            top_logit = 0.0
        extra_ms = (time.perf_counter() - started) * 1000.0
        updated = dict(row)
        updated["hits"] = hits
        updated["cross"] = top_logit
        updated["latency_ms"] = row["latency_ms"] + extra_ms
        updated["_pool"] = None
        scored.append(updated)
    return scored


def _tune(rows, kind, grid):
    best = None
    for threshold in grid:
        scored = _score(rows, kind, threshold, "dev")
        candidate = {
            "threshold": threshold,
            "objective": scored["objective"],
            "citation_accuracy": scored["citation_accuracy"],
            "recall_at_5": scored["recall_at_5"],
            "scored": scored,
        }
        if best is None or _better(candidate, best):
            best = candidate
    return best


def _better(left, right):
    return (
        left["objective"],
        left["citation_accuracy"],
        left["recall_at_5"],
        left["threshold"],
    ) > (
        right["objective"],
        right["citation_accuracy"],
        right["recall_at_5"],
        right["threshold"],
    )


def _score(rows, kind, threshold, split):
    ranks = []
    citations = []
    refusals = []
    accepts = []
    refuses = []
    latencies = []
    for row in rows:
        if split is not None and row.get("split") != split:
            continue
        latencies.append(row["latency_ms"])
        refused = _evidence(row, kind) < threshold
        if row["answerable"]:
            accepts.append(not refused)
            refusals.append(not refused)
            if refused:
                ranks.append(None)
                citations.append(False)
            else:
                ranks.append(_rank(row["hits"], row["doc_id"]))
                top = row["hits"][0] if row["hits"] else None
                citations.append(bool(
                    top
                    and top.get("doc_id") == row["doc_id"]
                    and row["key_phrase"]
                    and row["key_phrase"] in (top.get("text") or "")
                ))
        else:
            refuses.append(refused)
            refusals.append(refused)
    count = max(len(ranks), 1)
    recall_hits = [1.0 if rank is not None and rank <= TOP_K else 0.0 for rank in ranks]
    reciprocal = [0.0 if rank is None else 1.0 / rank for rank in ranks]
    accept_rate = sum(1.0 for item in accepts if item) / max(len(accepts), 1)
    refuse_rate = sum(1.0 for item in refuses if item) / max(len(refuses), 1)
    return {
        "recall_at_5": round(sum(recall_hits) / count, 4),
        "mrr": round(sum(reciprocal) / count, 4),
        "citation_accuracy": round(sum(1.0 for item in citations if item) / count, 4),
        "refusal_correctness": round(sum(1.0 for item in refusals if item) / max(len(refusals), 1), 4),
        "answerable_accept_rate": round(accept_rate, 4),
        "unanswerable_refuse_rate": round(refuse_rate, 4),
        "objective": round(0.5 * accept_rate + 0.5 * refuse_rate, 4),
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.50), 2),
            "p95": round(_percentile(latencies, 0.95), 2),
            "n": len(latencies),
        },
    }


def _public_metrics(scored, threshold, evidence):
    return {
        "recall_at_5": scored["recall_at_5"],
        "mrr": scored["mrr"],
        "citation_accuracy": scored["citation_accuracy"],
        "refusal_correctness": scored["refusal_correctness"],
        "answerable_accept_rate": scored["answerable_accept_rate"],
        "unanswerable_refuse_rate": scored["unanswerable_refuse_rate"],
        "threshold": threshold,
        "evidence": evidence,
        "latency_ms": scored["latency_ms"],
    }


def _tuning_record(choice, grid_note, rows, kind):
    values = [_evidence(row, kind) for row in rows if row.get("split") == "dev"]
    return {
        "grid": grid_note,
        "chosen_threshold": choice["threshold"],
        "dev_score_min": round(min(values), 4) if values else None,
        "dev_score_max": round(max(values), 4) if values else None,
        "dev": {
            "objective": choice["scored"]["objective"],
            "answerable_accept_rate": choice["scored"]["answerable_accept_rate"],
            "unanswerable_refuse_rate": choice["scored"]["unanswerable_refuse_rate"],
            "recall_at_5": choice["scored"]["recall_at_5"],
            "mrr": choice["scored"]["mrr"],
            "citation_accuracy": choice["scored"]["citation_accuracy"],
            "refusal_correctness": choice["scored"]["refusal_correctness"],
        },
    }


def _type_breakdown(rows, kind, threshold):
    order = []
    for row in rows:
        if row.get("split") not in (None, "test"):
            continue
        if row.get("type") not in order:
            order.append(row.get("type"))
    breakdown = {}
    for name in order:
        subset = [row for row in rows if row.get("type") == name and row.get("split") in (None, "test")]
        scored = _score(subset, kind, threshold, split=None)
        if name == "unanswerable":
            breakdown[name] = {
                "n": len(subset),
                "refusal_correctness": scored["refusal_correctness"],
            }
        else:
            breakdown[name] = {
                "n": len(subset),
                "recall_at_5": scored["recall_at_5"],
                "mrr": scored["mrr"],
                "citation_accuracy": scored["citation_accuracy"],
                "answerable_accept_rate": scored["answerable_accept_rate"],
            }
    return breakdown


def _evidence(row, kind):
    if kind == "support":
        return float(row["support"])
    if kind == "dense":
        return float(row["dense"])
    if kind == "cross":
        return float(row["cross"] or 0.0)
    raise ValueError(kind)


def _cross_grid(rows):
    values = sorted({round(float(row["cross"] or 0.0), 4) for row in rows if row.get("split") == "dev"})
    if not values:
        return [0.0]
    grid = [values[0] - 1.0]
    for left, right in zip(values, values[1:]):
        grid.append(round((left + right) / 2.0, 4))
    grid.append(values[-1] + 1.0)
    return grid


def _rank(hits, doc_id):
    for index, hit in enumerate(hits, start=1):
        if hit.get("doc_id") == doc_id:
            return index
    return None


def _percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _split_label(questions):
    splits = {item.get("split") for item in questions}
    if splits == {"test"}:
        return "test"
    if len(splits) == 1:
        return next(iter(splits))
    return "mixed"


def _versions():
    import importlib.metadata

    versions = {}
    for name in ("sentence-transformers", "torch"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


if __name__ == "__main__":
    main()
