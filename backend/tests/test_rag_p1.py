import json
import os

from pypdf import PdfWriter
from docx import Document

from app.models import db
from app.models.tech_summary import TechSummary
from app.rag.chunk import chunk_document
from app.rag.engine import HashEmbedder, tokenize
from app.rag.extract import extract_file
from app.rag.ingest import rebuild_from_db
from app.rag.store import SqliteVectorStore
from evals.run_eval import evaluate, load_jsonl
from evals.run_v2 import evaluate_hash
from tests.conftest import login


def test_chunking_keeps_heading_path_and_span():
    text = "# 总览\n第一句。\n## 细节\n石英舟要清洗。第二句。\n"
    chunks = chunk_document(text, title="记录", size=20, overlap=4)
    assert chunks
    assert any(chunk["section"].endswith("细节") for chunk in chunks)
    for chunk in chunks:
        assert text[chunk["span_start"]:chunk["span_end"]].strip()
        assert chunk["text"]


def test_store_upsert_persists_across_reopen(tmp_path):
    path = tmp_path / "index.sqlite"
    store = SqliteVectorStore(path)
    embedder = HashEmbedder()
    chunks = [{
        "section": "结论",
        "text": "编号 CODE-1001。关键结论：石英舟用稀释氢氟酸浸泡。",
        "span_start": 0,
        "span_end": 24,
        "source": "tech_summary",
    }]
    store.upsert_document(
        {
            "doc_id": "g01",
            "title": "石英舟",
            "source": "seed",
            "updated_at": "2026-01-15T00:00:00+00:00",
            "access_scope": "lab",
            "owner_id": 1,
        },
        chunks,
        embedder.embed([chunks[0]["text"]]),
    )
    store.close()
    reopened = SqliteVectorStore(path)
    assert reopened.get_document("g01")["title"] == "石英舟"
    assert list(reopened.iter_chunks())[0]["section"] == "结论"
    reopened.delete_document("g01")
    assert reopened.get_document("g01") is None
    reopened.close()


def test_blank_pdf_is_recorded_and_docx_text_is_kept(tmp_path, app):
    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(pdf_path, "wb") as handle:
        writer.write(handle)
    text, status = extract_file(pdf_path)
    assert text == ""
    assert status == "unsupported_scan"

    docx_path = tmp_path / "note.docx"
    document = Document()
    document.add_paragraph("附件里写着石英舟用稀释氢氟酸浸泡。")
    document.save(docx_path)
    extracted, docx_status = extract_file(docx_path)
    assert docx_status == "ok"
    assert "石英舟用稀释氢氟酸浸泡" in extracted

    with app.app_context():
        summary = TechSummary(
            title="带附件",
            content="正文没有附件句子。",
            summary_type="示例",
            user_id=1,
            file_path=str(pdf_path),
            access_scope="lab",
        )
        db.session.add(summary)
        db.session.commit()
        app.config["UPLOAD_FOLDER"] = str(tmp_path)
        rebuild_from_db()
        from app.rag.ingest import get_store
        assert get_store().failure_count("unsupported_scan") >= 1


def test_private_scope_hides_doc_from_other_members(client, app):
    headers = login(client, "member@example.com", "member-password-ok")
    admin = login(client, "admin@example.com", "admin-password-ok")
    created = client.post(
        "/api/v1/tech_summaries",
        json={
            "title": "私有记录",
            "content": "私有锚点 PRIVATE-ANCHOR-77 只允许作者和管理员检索。",
            "access_scope": "private",
        },
        headers=admin,
    )
    assert created.status_code == 201
    doc_id = created.get_json()["id"]
    hidden = client.get(f"/api/v1/tech_summaries/{doc_id}", headers=headers)
    assert hidden.status_code == 404
    app.config["RAG_ENABLED"] = True
    app.config["RAG_RETRIEVER"] = "hybrid_rerank"
    app.config["RAG_EMBEDDER"] = "hash"
    member_chat = client.post(
        "/api/v1/rag/chat",
        json={"query": "PRIVATE-ANCHOR-77"},
        headers=headers,
    )
    assert member_chat.status_code == 200
    assert member_chat.get_json()["code"] == "no_grounded_answer"
    assert "PRIVATE-ANCHOR-77" not in member_chat.get_data(as_text=True)
    admin_chat = client.post(
        "/api/v1/rag/chat",
        json={"query": "PRIVATE-ANCHOR-77"},
        headers=admin,
    )
    body = admin_chat.get_json()
    assert admin_chat.status_code == 503
    assert body["code"] == "llm_unavailable"
    assert body["sources"][0]["doc_id"] == str(doc_id)


def test_incremental_delete_drops_the_chunk(client, app):
    headers = login(client, "member@example.com", "member-password-ok")
    created = client.post(
        "/api/v1/tech_summaries",
        json={
            "title": "石英舟记录",
            "content": "关键结论：石英舟用稀释氢氟酸浸泡。",
            "access_scope": "lab",
        },
        headers=headers,
    )
    assert created.status_code == 201
    doc_id = created.get_json()["id"]
    app.config["RAG_ENABLED"] = True
    app.config["RAG_RETRIEVER"] = "hybrid_rerank"
    hit = client.post(
        "/api/v1/rag/chat",
        json={"query": "石英舟用稀释氢氟酸浸泡"},
        headers=headers,
    )
    assert hit.status_code == 503
    assert hit.get_json()["sources"]
    deleted = client.delete(f"/api/v1/tech_summaries/{doc_id}", headers=headers)
    assert deleted.status_code == 200
    missed = client.post(
        "/api/v1/rag/chat",
        json={"query": "石英舟用稀释氢氟酸浸泡"},
        headers=headers,
    )
    assert missed.status_code == 200
    assert missed.get_json()["code"] == "no_grounded_answer"


def test_stream_emits_citations_and_refusal_without_logging_the_query(client, app, monkeypatch):
    headers = login(client, "member@example.com", "member-password-ok")
    created = client.post(
        "/api/v1/tech_summaries",
        json={
            "title": "石英舟记录",
            "content": "关键结论：石英舟用稀释氢氟酸浸泡。",
            "access_scope": "lab",
        },
        headers=headers,
    )
    assert created.status_code == 201
    app.config["RAG_ENABLED"] = True
    app.config["RAG_RETRIEVER"] = "hybrid_rerank"
    app.config["AUDIT_EVENTS"].clear()

    def fake_stream(provider, messages):
        class _Tokens:
            usage = {"model": "fake-model", "prompt_tokens": 4, "completion_tokens": 3}
            model = "fake-model"

            def __iter__(self):
                yield "依据记录，"
                yield "需要浸泡。"

        return _Tokens()

    monkeypatch.setattr("app.api.v1.rag.stream", fake_stream)
    query = "石英舟用稀释氢氟酸浸泡"
    response = client.post("/api/v1/rag/chat/stream", json={"query": query}, headers=headers)
    payload = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "event: citations" in payload
    assert "event: token" in payload
    assert "event: done" in payload
    traces = [event for event in app.config["AUDIT_EVENTS"] if event["event"] == "rag_trace"]
    assert traces[-1]["outcome"] == "answered"
    assert traces[-1]["model"] == "fake-model"
    assert traces[-1]["prompt_tokens"] == 4
    assert traces[-1]["retrieval_ms"] >= 0
    assert traces[-1]["hit_ids"]
    dumped = json.dumps(traces, ensure_ascii=False)
    assert query not in dumped
    assert "关键结论" not in dumped

    refused = client.post(
        "/api/v1/rag/chat/stream",
        json={"query": "火星车太阳能板如何展开"},
        headers=headers,
    )
    body = refused.get_json()
    assert refused.status_code == 200
    assert body["code"] == "no_grounded_answer"


def test_eval_matches_committed_baseline():
    root = os.path.join(os.path.dirname(__file__), "..", "evals")
    documents = load_jsonl(os.path.join(root, "corpus.jsonl"))
    questions = load_jsonl(os.path.join(root, "questions.jsonl"))
    assert sum(1 for item in questions if item["answerable"]) >= 40
    assert sum(1 for item in questions if not item["answerable"]) >= 15
    report = evaluate(documents, questions)
    with open(os.path.join(root, "baseline_results.json"), encoding="utf-8") as handle:
        baseline = json.load(handle)
    assert report["modes"] == baseline["modes"]


def test_v2_hash_baseline_matches_and_questions_are_harder():
    import sys

    root = os.path.join(os.path.dirname(__file__), "..", "evals")
    documents = load_jsonl(os.path.join(root, "corpus_v2.jsonl"))
    questions = load_jsonl(os.path.join(root, "questions_v2.jsonl"))
    assert len(questions) >= 60
    assert {item["split"] for item in questions} == {"dev", "test"}
    assert sum(1 for item in questions if item["answerable"]) >= 40
    assert sum(1 for item in questions if not item["answerable"]) >= 20
    corpus_tokens = set()
    for row in documents:
        corpus_tokens.update(tokenize((row.get("title") or "") + "\n" + (row.get("content") or "")))
    for item in questions:
        assert item["set_version"] == "p1-v2"
        if item["answerable"]:
            assert item["key_phrase"] not in item["question"]
            assert item["type"] in {"paraphrase", "multichunk"}
        else:
            overlap = set(tokenize(item["question"])) & corpus_tokens
            assert len(overlap) >= 2
    test_questions = [item for item in questions if item["split"] == "test"]
    report = evaluate_hash(documents, test_questions)
    with open(os.path.join(root, "baseline_p1v2_hash.json"), encoding="utf-8") as handle:
        baseline = json.load(handle)
    assert baseline["embedder"] == "hash"
    assert baseline["split"] == "test"
    for mode in ("dense", "hybrid"):
        for key in ("recall_at_5", "mrr", "citation_accuracy", "refusal_correctness"):
            assert report["modes"][mode][key] == baseline["modes"][mode][key]
    assert "sentence_transformers" not in sys.modules
