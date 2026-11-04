import os

os.environ["SECRET_KEY"] = "test-secret-key-value-must-be-32b-x"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-value-must-be-32b-y"
os.environ["RAG_ENABLED"] = "false"
os.environ["RAG_RETRIEVER"] = "keyword"
os.environ["RAG_EMBEDDER"] = "hash"
os.environ["FLASK_DEBUG"] = "false"
os.environ["FLASK_CONFIG"] = "testing"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["AUTH_RATE_LIMIT"] = "10"
os.environ["CHAT_RATE_LIMIT"] = "20"

import pytest

from app import create_app
from app.models import db
from app.models.user import Role, User
from app.rate_limit import reset_rate_limits


@pytest.fixture
def app(tmp_path):
    os.environ["TEST_DATABASE_URL"] = "sqlite:///" + str(tmp_path / "test.sqlite")
    application = create_app("testing")
    application.config["AUDIT_EVENTS"] = []
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    application.config["UPLOAD_FOLDER"] = str(upload_root)
    application.config["RAG_INDEX_PATH"] = str(tmp_path / "rag.sqlite")
    application.config["RAG_EMBEDDER"] = "hash"
    with application.app_context():
        db.create_all()
        Role.insert_roles()
        admin = User(
            email="admin@example.com",
            username="demo-admin",
            password="admin-password-ok",
            name="示例管理员",
        )
        member = User(
            email="member@example.com",
            username="demo-member",
            password="member-password-ok",
            name="示例成员",
        )
        db.session.add(admin)
        db.session.add(member)
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()
    reset_rate_limits()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


def login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.get_data(as_text=True)
    return {"Authorization": f"Bearer {response.get_json()['access_token']}"}
