import logging
import uuid

from flask import Flask, g, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

from config import apply_runtime_config, config

jwt = JWTManager()
migrate = Migrate()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    apply_runtime_config(app)

    from app.models import db

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    _configure_audit_logger(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    @app.before_request
    def assign_request_id():
        g.request_id = uuid.uuid4().hex

    from app.api.v1 import api as api_v1_blueprint

    app.register_blueprint(api_v1_blueprint, url_prefix="/api/v1")
    return app


def _configure_audit_logger(app):
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = True
    path = app.config.get("AUDIT_LOG_PATH")
    if not path:
        return
    handler = logging.FileHandler(path)
    handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(handler)
    audit_logger.propagate = False
