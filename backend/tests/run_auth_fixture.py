"""Isolated real HTTP app for auth E2E. Never use this test fixture for deployment."""
import json
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
root = Path(os.environ['AUTH_E2E_DATA_DIR'])
os.environ['TEST_DATABASE_URL'] = 'sqlite:///' + str(root / 'auth.sqlite')
from app import create_app
from app.models import db, User, Role
from flask_jwt_extended import decode_token, create_access_token

app = create_app('testing')
app.config['UPLOAD_FOLDER'] = str(root / 'uploads')
with app.app_context():
    db.create_all()
    Role.insert_roles()
    for role, name in [('Administrator', 'auth-admin'), ('User', 'auth-member'), ('Moderator', 'auth-moderator')]:
        db.session.add(User(email=name + '@example.test', username=name, password='FixturePass123!',
                            role=Role.query.filter_by(name=role).one()))
    db.session.commit()
    client = app.test_client()
    data = client.post('/api/v1/auth/login', json={
        'email': 'auth-member@example.test', 'password': 'FixturePass123!',
    }).get_json()
    claims = decode_token(data['access_token'])
    data['expired_token'] = create_access_token(identity=claims['sub'], additional_claims={'sid': claims['sid']},
                                               expires_delta=timedelta(seconds=-1))
    (root / 'seed.json').write_text(json.dumps(data))
app.run(host='127.0.0.1', port=5103, use_reloader=False)
