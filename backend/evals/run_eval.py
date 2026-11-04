"""Offline retrieval eval. Hash embeddings only, unless --judge is passed.

From the backend directory::

    python -m evals.run_eval
    python -m evals.run_eval --write-baseline
    python -m evals.run_eval --judge
"""
import argparse
import json
import os
import tempfile

from app.rag.engine import HashEmbedder
from app.rag.ingest import index_corpus_rows
from app.rag.store import SqliteVectorStore


MODES = ("dense", "hybrid", "hybrid_rerank")
THRESHOLD = 0.12


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def evaluate(documents, questions, top_k=5, threshold=THRESHOLD):
    directory = tempfile.mkdtemp(prefix="rag-eval-")
    path = os.path.join(directory, "index.sqlite")
    store = SqliteVectorStore(path)
    embedder = HashEmbedder()
    index_corpus_rows(documents, store, embedder)
    chunks = list(store.iter_chunks())
    store.close()
    from app.rag.engine import search_chunks

    report = {"set_version": questions[0].get("set_version") if questions else None, "embedder": "hash", "modes": {}}
    for mode in MODES:
        ranks = []
        citations = []
        refusals = []
        for item in questions:
            result = search_chunks(
                chunks,
                item["question"],
                embedder,
                mode=mode,
                top_k=top_k,
                threshold=threshold,
            )
            refused = bool(result["refused"])
            if item["answerable"]:
                refusals.append(not refused)
                rank = _rank(result["hits"], item["doc_id"])
                ranks.append(rank)
                top = result["hits"][0] if result["hits"] else None
                citations.append(bool(
                    top
                    and top.get("doc_id") == item["doc_id"]
                    and item["key_phrase"]
                    and item["key_phrase"] in (top.get("text") or "")
                ))
            else:
                refusals.append(refused)
        report["modes"][mode] = _metrics(ranks, citations, refusals, top_k)
    report["answerable"] = sum(1 for item in questions if item["answerable"])
    report["unanswerable"] = sum(1 for item in questions if not item["answerable"])
    report["top_k"] = top_k
    report["threshold"] = threshold
    report["notes"] = (
        "Deterministic hash embedder plus BM25. "
        "hybrid_rerank uses the overlap reranker, not a downloaded cross-encoder."
    )
    return report


def _rank(hits, doc_id):
    for index, hit in enumerate(hits, start=1):
        if hit.get("doc_id") == doc_id:
            return index
    return None


def _metrics(ranks, citations, refusals, top_k):
    recall_hits = [1.0 if rank is not None and rank <= top_k else 0.0 for rank in ranks]
    reciprocal = [0.0 if rank is None else 1.0 / rank for rank in ranks]
    count = max(len(ranks), 1)
    refusal_count = max(len(refusals), 1)
    return {
        "recall_at_5": round(sum(recall_hits) / count, 4),
        "mrr": round(sum(reciprocal) / count, 4),
        "citation_accuracy": round(sum(1.0 for item in citations if item) / count, 4),
        "refusal_correctness": round(sum(1.0 for item in refusals if item) / refusal_count, 4),
    }


def render(report):
    lines = [
        f"set={report.get('set_version')} embedder={report.get('embedder')} "
        f"answerable={report.get('answerable')} unanswerable={report.get('unanswerable')}",
        f"{'mode':<16} {'Recall@5':>10} {'MRR':>10} {'citation':>10} {'refusal':>10}",
    ]
    for mode, metrics in report["modes"].items():
        lines.append(
            f"{mode:<16} {metrics['recall_at_5']:>10.4f} {metrics['mrr']:>10.4f} "
            f"{metrics['citation_accuracy']:>10.4f} {metrics['refusal_correctness']:>10.4f}"
        )
    return "\n".join(lines)


def maybe_judge(questions, documents, provider):
    """Optional faithfulness check. Off unless --judge is passed."""
    from app.rag.llm import complete

    by_id = {row["doc_id"]: row["content"] for row in documents}
    scored = 0
    faithful = 0
    for item in questions:
        if not item["answerable"]:
            continue
        context = by_id.get(item["doc_id"]) or ""
        messages = [
            {"role": "system", "content": "只回答 yes 或 no。判断回答是否只包含给定材料中的事实。"},
            {"role": "user", "content": f"材料：{context}\n要点：{item['key_phrase']}\n这段材料是否包含要点？"},
        ]
        result = complete(provider, messages)
        if not result:
            print("judge skipped: provider unavailable")
            return
        scored += 1
        if "yes" in (result.get("text") or "").lower():
            faithful += 1
        if scored >= 5:
            break
    if scored:
        print(f"judge_sample={scored} faithful={faithful / scored:.2f}")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)
    root = os.path.dirname(__file__)
    documents = load_jsonl(os.path.join(root, "corpus.jsonl"))
    questions = load_jsonl(os.path.join(root, "questions.jsonl"))
    report = evaluate(documents, questions, top_k=args.top_k)
    print(render(report))
    if args.write_baseline:
        path = os.path.join(root, "baseline_results.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"wrote {path}")
    if args.judge:
        maybe_judge(questions, documents, args.provider)
    return report


if __name__ == "__main__":
    main()
