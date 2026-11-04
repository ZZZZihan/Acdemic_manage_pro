import json
import os
import subprocess
import sys

import pytest

from app.models.tech_summary import TechSummary
from app.models import db
from tests.conftest import login


def test_app_boots_with_debug_off(client, app):
    assert app.config["DEBUG"] is False
    response = client.get("/api/v1/achievements")
    assert response.status_code == 200


def test_missing_jwt_secret_refuses_start(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "jwt-secret-key")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-value-must-be-32b-x")
    from app import create_app

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app("testing")


def test_wildcard_cors_refuses_start(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    from app import create_app

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        create_app("testing")


def test_chat_and_directory_require_auth(client):
    assert client.post("/api/v1/rag/chat", json={"query": "demo"}).status_code == 401
    assert client.post("/api/v1/knowledge_base/chat", json={"query": "demo"}).status_code == 401
    assert client.get("/api/v1/users").status_code == 401
    assert client.get("/api/v1/meetings/1").status_code == 401
    assert client.get("/api/v1/files/download/missing.txt").status_code == 401
    assert client.get("/api/v1/projects").status_code == 401


def test_rag_disabled_is_explicit_503(client):
    headers = login(client, "member@example.com", "member-password-ok")
    response = client.post("/api/v1/rag/chat", json={"query": "demo-corpus-anchor"}, headers=headers)
    body = response.get_json()
    assert response.status_code == 503
    assert body["code"] == "rag_unavailable"
    assert body["success"] is False


def test_no_hit_does_not_invent_an_answer(client, app):
    headers = login(client, "member@example.com", "member-password-ok")
    with app.app_context():
        admin_id = 1
        db.session.add(TechSummary(
            title="示例技术总结",
            content="实验室示例语料，仅包含标记 demo-corpus-anchor。",
            summary_type="示例",
            user_id=admin_id,
        ))
        db.session.commit()
    app.config["RAG_ENABLED"] = True
    app.config["RAG_RETRIEVER"] = "keyword"
    response = client.post(
        "/api/v1/rag/chat",
        json={"query": "完全无关的问题"},
        headers=headers,
    )
    body = response.get_json()
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert body["code"] == "no_grounded_answer"
    assert "学习建议" not in text
    assert "fallback_deepseek" not in text


def test_hit_without_llm_is_503(client, app):
    headers = login(client, "member@example.com", "member-password-ok")
    with app.app_context():
        db.session.add(TechSummary(
            title="示例技术总结",
            content="实验室示例语料，仅包含标记 demo-corpus-anchor。",
            summary_type="示例",
            user_id=1,
        ))
        db.session.commit()
    app.config["RAG_ENABLED"] = True
    app.config["RAG_RETRIEVER"] = "keyword"
    response = client.post(
        "/api/v1/rag/chat",
        json={"query": "demo-corpus-anchor"},
        headers=headers,
    )
    body = response.get_json()
    assert response.status_code == 503
    assert body["code"] == "llm_unavailable"
    assert body["sources"]
    assert "学习建议" not in response.get_data(as_text=True)


def test_admin_rebuild_matches_rows_and_member_is_forbidden(client, app):
    with app.app_context():
        db.session.add(TechSummary(
            title="示例技术总结",
            content="实验室示例语料，仅包含标记 demo-corpus-anchor。",
            summary_type="示例",
            user_id=1,
        ))
        db.session.commit()
        rows = TechSummary.query.count()
    member = login(client, "member@example.com", "member-password-ok")
    denied = client.post("/api/v1/rag/init_flashrag", headers=member)
    assert denied.status_code == 403
    admin = login(client, "admin@example.com", "admin-password-ok")
    rebuilt = client.post("/api/v1/rag/init_flashrag", headers=admin)
    body = rebuilt.get_json()
    assert rebuilt.status_code == 200
    assert body["corpus_docs"] == rows
    assert body["tech_summary_rows"] == rows
    assert body["corpus_matches_rows"] is True


def test_directory_redacts_other_emails(client):
    headers = login(client, "member@example.com", "member-password-ok")
    response = client.get("/api/v1/users", headers=headers)
    rows = response.get_json()
    assert response.status_code == 200
    member = next(row for row in rows if row["username"] == "demo-member")
    admin = next(row for row in rows if row["username"] == "demo-admin")
    assert member["email"] == "member@example.com"
    assert "email" not in admin


def test_login_audit_omits_secrets_and_email(client, app):
    login(client, "member@example.com", "member-password-ok")
    events = app.config["AUDIT_EVENTS"]
    dumped = json.dumps(events, ensure_ascii=False)
    assert any(event["event"] == "login_success" for event in events)
    assert "member@example.com" not in dumped
    assert "member-password-ok" not in dumped
    assert "access_token" not in dumped
    assert "Bearer" not in dumped


def test_auth_rate_limit(client, app):
    app.config["AUTH_RATE_LIMIT"] = 2
    payload = {"email": "member@example.com", "password": "wrong-password-value"}
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    limited = client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert limited.get_json()["code"] == "rate_limited"


def test_file_download_is_audited(client, app):
    upload = app.config["UPLOAD_FOLDER"]
    with open(os.path.join(upload, "note.txt"), "w", encoding="utf-8") as handle:
        handle.write("demo")
    headers = login(client, "member@example.com", "member-password-ok")
    response = client.get("/api/v1/files/download/note.txt", headers=headers)
    assert response.status_code == 200
    assert response.data == b"demo"
    events = [event for event in app.config["AUDIT_EVENTS"] if event["event"] == "file_download"]
    assert events[-1]["filename"] == "note.txt"
    traversal = client.get("/api/v1/files/download/../note.txt", headers=headers)
    assert traversal.status_code == 404


def test_import_does_not_load_embedding_stack():
    backend = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    env.update({
        "SECRET_KEY": "test-secret-key-value-must-be-32b-x",
        "JWT_SECRET_KEY": "test-jwt-secret-value-must-be-32b-y",
        "RAG_ENABLED": "false",
        "FLASK_CONFIG": "testing",
        "PYTHONPATH": backend,
    })
    code = (
        "import sys\n"
        "from app import create_app\n"
        "create_app('testing')\n"
        "for name in ('torch', 'sentence_transformers', 'faiss'):\n"
        "    assert name not in sys.modules, name\n"
    )
    subprocess.check_call([sys.executable, "-c", code], cwd=backend, env=env)
