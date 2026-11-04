import os
import secrets
from pathlib import Path
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = None
    JWT_SECRET_KEY = None
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 设置最大上传文件大小为10MB
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    @staticmethod
    def init_app(app):
        key = os.environ.get('JWT_SECRET_KEY')
        if not key and app.testing:
            key = 'test-only-jwt-secret-not-for-production-' * 2
        if not key and app.config.get('REQUIRE_AUTH_SECRET'):
            raise RuntimeError('Production requires JWT_SECRET_KEY (at least 32 characters)')
        if not key:
            path = Path(app.instance_path) / '.jwt-secret'
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(fd, 'w') as handle:
                    handle.write(secrets.token_hex(32))
            key = path.read_text().strip()
        if len(key) < 32 or key in {'hard-to-guess-string', 'jwt-secret-key'}:
            raise RuntimeError('JWT_SECRET_KEY must contain at least 32 characters')
        app.config['JWT_SECRET_KEY'] = key
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or key
        env_key = 'TEST_DATABASE_URL' if app.testing else ('DEV_DATABASE_URL' if app.debug else 'DATABASE_URL')
        if os.environ.get(env_key):
            app.config['SQLALCHEMY_DATABASE_URI'] = os.environ[env_key]

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')

class ProductionConfig(Config):
    REQUIRE_AUTH_SECRET = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 