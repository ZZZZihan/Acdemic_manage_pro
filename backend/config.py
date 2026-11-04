import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

# Values that have shipped in this repository or in example configs.
# They must never be accepted as a runtime secret.
_WEAK_SECRETS = {
    "",
    "secret",
    "changeme",
    "jwt-secret-key",
    "your-jwt-secret-key",
    "your-secret-key",
    "hard-to-guess-string",
    "dev-secret-key",
    "replace-with-at-least-32-random-characters",
    "replace-with-another-32-plus-random-characters",
}

_MIN_SECRET_LENGTH = 32


def _env_flag(name, default="false"):
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _parse_origins(raw):
    origins = [item.strip() for item in (raw or "").split(",") if item.strip()]
    if not origins or "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS must be a comma-separated allowlist of origins. "
            "Wildcard origins are not accepted."
        )
    return origins


def _check_secret(name, value):
    candidate = (value or "").strip()
    if len(candidate) < _MIN_SECRET_LENGTH or candidate.lower() in _WEAK_SECRETS:
        raise RuntimeError(
            f"{name} must be provided via the environment as a random string "
            f"of at least {_MIN_SECRET_LENGTH} characters. Refusing to start "
            "with a missing, short, or well-known secret."
        )
    return candidate


def validate_runtime_secrets():
    """Fail closed unless both application secrets are strong and explicit."""
    return {
        "SECRET_KEY": _check_secret("SECRET_KEY", os.environ.get("SECRET_KEY")),
        "JWT_SECRET_KEY": _check_secret("JWT_SECRET_KEY", os.environ.get("JWT_SECRET_KEY")),
    }


class Config:
    SECRET_KEY = None
    JWT_SECRET_KEY = None
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    DEBUG = False
    TESTING = False
    RAG_ENABLED = False
    RAG_RETRIEVER = "hybrid_rerank"
    RAG_EMBEDDER = "hash"
    RAG_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    RAG_RERANKER = "overlap"
    RAG_SCORE_THRESHOLD = 0.12
    # Cosine / cross-encoder cutoffs used only when the embedder is bge.
    # Chosen on the p1-v2 dev split; see backend/evals/baseline_p1v2_bge.json.
    RAG_DENSE_SCORE_THRESHOLD = 0.60
    RAG_HYBRID_DENSE_SCORE_THRESHOLD = 0.62
    RAG_RERANK_SCORE_THRESHOLD = 0.8981
    RAG_RERANK_POOL = 15
    RAG_INDEX_PATH = os.path.join(basedir, "instance", "rag_index.sqlite")
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    AUTH_RATE_LIMIT = 10
    AUTH_RATE_WINDOW_SECONDS = 60
    CHAT_RATE_LIMIT = 20
    CHAT_RATE_WINDOW_SECONDS = 60
    AUDIT_LOG_PATH = None
    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or (
        "sqlite:///" + os.path.join(basedir, "data-dev.sqlite")
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(basedir, "data.sqlite")
    )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def apply_runtime_config(app):
    """Overlay environment-driven settings after the class defaults load.

    Class attributes are not a place to read secrets: import time must not
    capture a weak fallback, and tests must be able to change the environment
    before ``create_app`` runs.
    """
    secrets = validate_runtime_secrets()
    app.config["SECRET_KEY"] = secrets["SECRET_KEY"]
    app.config["JWT_SECRET_KEY"] = secrets["JWT_SECRET_KEY"]
    app.config["DEBUG"] = _env_flag("FLASK_DEBUG", "false")
    app.config["RAG_ENABLED"] = _env_flag("RAG_ENABLED", "false")
    app.config["RAG_RETRIEVER"] = os.environ.get("RAG_RETRIEVER", "hybrid_rerank").strip().lower()
    app.config["RAG_EMBEDDER"] = os.environ.get("RAG_EMBEDDER", "hash").strip().lower()
    app.config["RAG_EMBEDDING_MODEL"] = os.environ.get(
        "RAG_EMBEDDING_MODEL",
        "BAAI/bge-small-zh-v1.5",
    )
    app.config["RAG_RERANKER"] = os.environ.get("RAG_RERANKER", "overlap").strip().lower()
    app.config["RAG_SCORE_THRESHOLD"] = float(os.environ.get("RAG_SCORE_THRESHOLD", "0.12"))
    app.config["RAG_DENSE_SCORE_THRESHOLD"] = float(os.environ.get("RAG_DENSE_SCORE_THRESHOLD", "0.60"))
    app.config["RAG_HYBRID_DENSE_SCORE_THRESHOLD"] = float(
        os.environ.get("RAG_HYBRID_DENSE_SCORE_THRESHOLD", "0.62")
    )
    app.config["RAG_RERANK_SCORE_THRESHOLD"] = float(os.environ.get("RAG_RERANK_SCORE_THRESHOLD", "0.8981"))
    app.config["RAG_RERANK_POOL"] = int(os.environ.get("RAG_RERANK_POOL", "15"))
    app.config["RAG_INDEX_PATH"] = os.environ.get(
        "RAG_INDEX_PATH",
        os.path.join(basedir, "instance", "rag_index.sqlite"),
    )
    app.config["CORS_ORIGINS"] = _parse_origins(
        os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )
    app.config["AUTH_RATE_LIMIT"] = int(os.environ.get("AUTH_RATE_LIMIT", "10"))
    app.config["AUTH_RATE_WINDOW_SECONDS"] = int(os.environ.get("AUTH_RATE_WINDOW_SECONDS", "60"))
    app.config["CHAT_RATE_LIMIT"] = int(os.environ.get("CHAT_RATE_LIMIT", "20"))
    app.config["CHAT_RATE_WINDOW_SECONDS"] = int(os.environ.get("CHAT_RATE_WINDOW_SECONDS", "60"))
    audit_path = os.environ.get("AUDIT_LOG_PATH", "").strip()
    app.config["AUDIT_LOG_PATH"] = audit_path or None
    if app.config["TESTING"]:
        uri = os.environ.get("TEST_DATABASE_URL")
        if uri:
            app.config["SQLALCHEMY_DATABASE_URI"] = uri
