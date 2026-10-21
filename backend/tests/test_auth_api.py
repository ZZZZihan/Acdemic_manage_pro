import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from datetime import timedelta
import os

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix='auth-api-tests-'))

class TestAuthAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app
        from app.models import Role, db
        from config import config

        cls.Role = Role
        cls.db = db
        cls.original_test_db_uri = config['testing'].SQLALCHEMY_DATABASE_URI
        config['testing'].SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB_DIR / 'data-test.sqlite'}"
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.db.session.remove()
        cls.app_context.pop()
        from config import config
        config['testing'].SQLALCHEMY_DATABASE_URI = cls.original_test_db_uri
        for module_name in list(sys.modules):
            if module_name == 'app' or module_name.startswith('app.'):
                sys.modules.pop(module_name, None)
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self):
        self.db.session.remove()
        self.db.drop_all()
        self.db.create_all()
        self.Role.insert_roles()
        self.client = self.app.test_client()

    def tearDown(self):
        self.db.session.remove()

    def register_user(self, **overrides):
        payload = {
            'email': 'tester@example.com',
            'username': 'tester',
            'password': 'Secret123!',
            'name': 'Tester',
        }
        payload.update(overrides)
        return self.client.post('/api/v1/auth/register', json=payload)

    def login_user(self, password='Secret123!'):
        return self.client.post('/api/v1/auth/login', json={
            'email': 'tester@example.com',
            'password': password,
        })

    @staticmethod
    def auth_headers(token):
        return {
            'Authorization': f'Bearer {token}',
        }

    def test_register_returns_created_user(self):
        response = self.register_user()

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload['message'], '注册成功')
        self.assertEqual(payload['user']['email'], 'tester@example.com')
        self.assertEqual(payload['user']['username'], 'tester')
        self.assertNotIn('password_hash', payload['user'])

    def test_register_rejects_duplicate_email(self):
        self.register_user()

        response = self.register_user(username='another-user')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], '邮箱已被注册')

    def test_register_rejects_blank_required_fields(self):
        response = self.register_user(email='   ', username=' ', password='   ')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], '邮箱、用户名和密码不能为空')

    def test_register_rejects_non_string_credentials(self):
        response = self.register_user(email=True, username=123, password=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['message'], '邮箱、用户名和密码必须是字符串')

    def test_login_returns_access_and_refresh_tokens(self):
        self.register_user()

        response = self.login_user()

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('access_token', payload)
        self.assertIn('refresh_token', payload)
        self.assertEqual(payload['user']['username'], 'tester')

    def test_login_accepts_trimmed_email_input(self):
        self.register_user(email='  tester@example.com  ')

        response = self.client.post('/api/v1/auth/login', json={
            'email': '  tester@example.com  ',
            'password': 'Secret123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.get_json())

    def test_login_rejects_invalid_password(self):
        self.register_user()

        response = self.login_user(password='invalid123')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['message'], '邮箱或密码错误')

    def test_current_user_endpoint_returns_role_metadata(self):
        self.register_user()
        login_response = self.login_user()
        access_token = login_response.get_json()['access_token']

        response = self.client.get('/api/v1/auth/user', headers=self.auth_headers(access_token))

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['username'], 'tester')
        self.assertEqual(payload['role'], 'User')
        self.assertFalse(payload['is_administrator'])
        self.assertEqual(payload['permissions'], 1)

    def test_refresh_returns_new_access_token(self):
        self.register_user()
        login_response = self.login_user()
        refresh_token = login_response.get_json()['refresh_token']

        response = self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(refresh_token))

        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.get_json())

    def test_health_endpoint_reports_backend_v1(self):
        response = self.client.get('/api/v1/health')

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['service'], 'backend-v1')


    def login_as(self, email='tester@example.com'):
        return self.client.post('/api/v1/auth/login', json={
            'email': email, 'password': 'Secret123!',
        }).get_json()

    def make_user(self, role='User', email='tester@example.com', username='tester'):
        from app.models import User
        user = User(email=email, username=username, password='Secret123!',
                    role=self.Role.query.filter_by(name=role).one())
        self.db.session.add(user)
        self.db.session.commit()
        return user.id

    def test_special_admin_email_and_role_injection_are_normal_members(self):
        response = self.register_user(email='admin@example.com', role='Administrator',
                                      role_id=3, permissions=7)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['user']['role'], 'User')
        self.assertFalse(response.get_json()['user']['is_administrator'])

    def test_all_roles_are_returned_at_login(self):
        for index, (role, permissions) in enumerate([('User', 1), ('Moderator', 3), ('Administrator', 7)]):
            email = f'role{index}@example.com'
            self.make_user(role, email, f'role{index}')
            user = self.login_as(email)['user']
            self.assertEqual((user['role'], user['permissions']), (role, permissions))
            self.assertEqual(user['is_administrator'], role == 'Administrator')

    def test_admin_assigns_role_and_existing_token_sees_live_permissions(self):
        self.make_user('Administrator', 'manager@example.com', 'manager')
        target_id = self.make_user()
        member = self.login_as()
        admin = self.login_as('manager@example.com')
        headers = self.auth_headers(admin['access_token'])
        response = self.client.put(f'/api/v1/users/{target_id}/role', headers=headers, json={'role': 'Moderator'})
        self.assertEqual(response.status_code, 200)
        profile = self.client.get('/api/v1/auth/user', headers=self.auth_headers(member['access_token']))
        self.assertEqual(profile.get_json()['role'], 'Moderator')
        self.assertEqual(profile.get_json()['permissions'], 3)

    def test_member_and_moderator_cannot_assign_roles(self):
        target_id = self.make_user()
        for role in ['User', 'Moderator']:
            self.make_user(role, f'{role}@example.com', role)
            tokens = self.login_as(f'{role}@example.com')
            headers = self.auth_headers(tokens['access_token'])
            self.assertEqual(self.client.get('/api/v1/roles', headers=headers).status_code, 403)
            self.assertEqual(self.client.put(f'/api/v1/users/{target_id}/role', headers=headers,
                                             json={'role': 'Administrator'}).status_code, 403)

    def test_demoted_administrator_loses_permission_with_same_jwt(self):
        self.make_user('Administrator', 'a@example.com', 'a')
        target_id = self.make_user('Administrator', 'b@example.com', 'b')
        first, second = self.login_as('a@example.com'), self.login_as('b@example.com')
        self.client.put(f'/api/v1/users/{target_id}/role', headers=self.auth_headers(first['access_token']),
                        json={'role': 'User'})
        self.assertEqual(self.client.get('/api/v1/roles', headers=self.auth_headers(second['access_token'])).status_code, 403)

    def test_demotion_applies_to_existing_business_token_and_refresh(self):
        from app.models import Meeting
        from datetime import datetime
        first_id = self.make_user('Administrator', 'a@example.com', 'a')
        second_id = self.make_user('Administrator', 'b@example.com', 'b')
        meetings = [Meeting(title=title, organizer_id=first_id,
                            start_time=datetime.utcnow(), end_time=datetime.utcnow())
                    for title in ('Before demotion', 'After demotion')]
        self.db.session.add_all(meetings)
        self.db.session.commit()
        first, second = self.login_as('a@example.com'), self.login_as('b@example.com')
        existing = self.auth_headers(second['access_token'])
        self.assertEqual(self.client.delete(f'/api/v1/meetings/{meetings[0].id}', headers=existing).status_code, 200)
        changed = self.client.put(f'/api/v1/users/{second_id}/role',
            headers=self.auth_headers(first['access_token']), json={'role': 'User'})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.delete(f'/api/v1/meetings/{meetings[1].id}', headers=existing).status_code, 403)
        self.assertIsNotNone(Meeting.query.get(meetings[1].id))
        refreshed = self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(second['refresh_token']))
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.get_json()['user']['role'], 'User')
        self.assertEqual(self.client.get('/api/v1/roles',
            headers=self.auth_headers(refreshed.get_json()['access_token'])).status_code, 403)

    def test_cannot_demote_self_or_assign_unknown_role(self):
        user_id = self.make_user('Administrator')
        headers = self.auth_headers(self.login_as()['access_token'])
        self.assertEqual(self.client.put(f'/api/v1/users/{user_id}/role', headers=headers,
                                        json={'role': 'User'}).status_code, 403)
        self.assertEqual(self.client.put(f'/api/v1/users/{user_id}/role', headers=headers,
                                        json={'role': 'Owner'}).status_code, 400)

    def test_anonymous_cannot_read_members_or_assign_role(self):
        for path in ['/api/v1/users', '/api/v1/users/current', '/api/v1/roles']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.put('/api/v1/users/1/role', json={'role': 'Administrator'}).status_code, 401)

    def test_refresh_rejects_access_token_and_user_endpoint_rejects_refresh_token(self):
        self.register_user()
        tokens = self.login_as()
        self.assertEqual(self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(tokens['access_token'])).status_code, 401)
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=self.auth_headers(tokens['refresh_token'])).status_code, 401)

    def test_expired_access_can_refresh_but_expired_refresh_is_rejected(self):
        from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
        self.register_user()
        tokens = self.login_as()
        claims = decode_token(tokens['access_token'])
        expired = create_access_token(identity=claims['sub'], additional_claims={'sid': claims['sid']},
                                      expires_delta=timedelta(seconds=-1))
        response = self.client.get('/api/v1/auth/user', headers=self.auth_headers(expired))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['code'], 'token_expired')
        self.assertEqual(self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(tokens['refresh_token'])).status_code, 200)
        expired_refresh = create_refresh_token(identity=claims['sub'], additional_claims={'sid': claims['sid']},
                                              expires_delta=timedelta(seconds=-1))
        self.assertEqual(self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(expired_refresh)).status_code, 401)

    def test_logout_revokes_both_tokens_and_preserves_other_device(self):
        self.register_user()
        first, second = self.login_as(), self.login_as()
        self.assertEqual(self.client.post('/api/v1/auth/logout', headers=self.auth_headers(first['refresh_token'])).status_code, 200)
        self.db.session.remove()
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=self.auth_headers(first['access_token'])).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(first['refresh_token'])).status_code, 401)
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=self.auth_headers(second['access_token'])).status_code, 200)

    def test_session_and_revocation_survive_app_recreation(self):
        from app import create_app
        self.register_user()
        tokens = self.login_as()
        self.db.session.remove()
        restarted = create_app('testing')
        with restarted.app_context():
            client = restarted.test_client()
            self.assertEqual(client.get('/api/v1/auth/user',
                headers=self.auth_headers(tokens['access_token'])).status_code, 200)
            self.assertEqual(client.post('/api/v1/auth/logout',
                headers=self.auth_headers(tokens['refresh_token'])).status_code, 200)
        self.db.session.remove()
        self.assertEqual(self.client.get('/api/v1/auth/user',
            headers=self.auth_headers(tokens['access_token'])).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/refresh',
            headers=self.auth_headers(tokens['refresh_token'])).status_code, 401)

    def test_tampered_and_legacy_tokens_are_rejected(self):
        import jwt
        from flask_jwt_extended import create_access_token, decode_token
        self.register_user()
        token = self.login_as()['access_token']
        payload = decode_token(token)
        tampered = jwt.encode(payload, 'a-different-signing-secret-' * 3, algorithm='HS256')
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=self.auth_headers(tampered)).status_code, 401)
        legacy = create_access_token(identity=payload['sub'])
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=self.auth_headers(legacy)).status_code, 401)

    def test_deleted_user_cannot_refresh(self):
        from app.models import User
        self.register_user()
        tokens = self.login_as()
        self.db.session.delete(User.query.filter_by(email='tester@example.com').one())
        self.db.session.commit()
        self.assertEqual(self.client.post('/api/v1/auth/refresh', headers=self.auth_headers(tokens['refresh_token'])).status_code, 401)

    def test_non_object_payload_is_bad_request(self):
        for value in [[], ['email'], True, 'bad']:
            for path in ['/api/v1/auth/login', '/api/v1/auth/register']:
                self.assertEqual(self.client.post(path, json=value).status_code, 400)

    def test_auth_initialization_is_idempotent_and_repairs_unassigned_users(self):
        from app.models import User
        user_id = self.make_user('Administrator')
        other_id = self.make_user(email='other@example.com', username='other')
        User.query.get(other_id).role = None
        self.db.session.commit()
        runner = self.app.test_cli_runner()
        for _ in range(2):
            result = runner.invoke(args=['init-auth'])
            self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(User.query.get(user_id).role.name, 'Administrator')
        self.assertEqual(User.query.get(other_id).role.name, 'User')

    def test_production_requires_secret_and_reads_late_environment(self):
        from app import create_app
        with mock.patch.dict(os.environ, {'JWT_SECRET_KEY': ''}):
            with self.assertRaises(RuntimeError):
                create_app('production')
        key = 'late-loaded-production-secret-' * 3
        with mock.patch.dict(os.environ, {'JWT_SECRET_KEY': key}):
            app = create_app('production')
            self.assertEqual(app.config['JWT_SECRET_KEY'], key)


    def test_string_jwt_subject_can_access_own_meeting_files_and_cannot_delete_others(self):
        from app.models import Meeting
        from datetime import datetime
        owner = self.make_user()
        other = self.make_user(email='other@example.com', username='other')
        meeting = Meeting(title='JWT role check', organizer_id=owner,
                          start_time=datetime.utcnow(), end_time=datetime.utcnow())
        self.db.session.add(meeting)
        self.db.session.commit()
        owner_headers = self.auth_headers(self.login_as()['access_token'])
        other_headers = self.auth_headers(self.login_as('other@example.com')['access_token'])
        self.assertEqual(self.client.get(f'/api/v1/meetings/{meeting.id}/files', headers=owner_headers).status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/meetings/{meeting.id}/files', headers=other_headers).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/meetings/{meeting.id}', headers=other_headers).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/v1/meetings/{meeting.id}', headers=owner_headers).status_code, 200)

    def test_business_permission_denial_is_403_and_does_not_invalidate_session(self):
        from app.models import Achievement
        owner = self.make_user()
        self.make_user(email='other@example.com', username='other')
        item = Achievement(title='Private edit', user_id=owner)
        self.db.session.add(item)
        self.db.session.commit()
        headers = self.auth_headers(self.login_as('other@example.com')['access_token'])
        self.assertEqual(self.client.delete(f'/api/v1/achievements/{item.id}', headers=headers).status_code, 403)
        self.assertEqual(self.client.get('/api/v1/auth/user', headers=headers).status_code, 200)

    def test_project_physical_delete_preserves_untrusted_paths_and_references(self):
        from app.models.project import Project, ProjectFile
        owner = self.make_user()
        project = Project(name='Owner project', creator_id=owner)
        self.db.session.add(project)
        self.db.session.commit()
        headers = self.auth_headers(self.login_as()['access_token'])
        with tempfile.TemporaryDirectory(prefix='auth-upload-boundary-') as directory:
            root = Path(directory)
            uploads = root / 'uploads'
            uploads.mkdir()
            outside = root / 'outside.txt'
            outside.write_text('synthetic outside sentinel')
            unrelated = uploads / 'another-users-upload.txt'
            unrelated.write_text('synthetic unrelated upload')
            (uploads / 'link.txt').symlink_to(outside)
            with mock.patch.dict(self.app.config, {'UPLOAD_FOLDER': str(uploads)}):
                for path in [str(outside), '../outside.txt', 'link.txt', unrelated.name]:
                    with self.subTest(path=path):
                        # A valid JWT and a self-owned project must not turn a
                        # client-provided attachment path into deletion authority.
                        attached = self.client.post(f'/api/v1/projects/{project.id}/files',
                            headers=headers, json={'file_path': path, 'original_name': 'fixture.txt'})
                        self.assertEqual(attached.status_code, 201)
                        file_id = attached.get_json()['id']
                        response = self.client.delete(
                            f'/api/v1/projects/{project.id}/files/{file_id}/physical', headers=headers)
                        self.assertEqual(response.status_code, 409)
                        self.assertEqual(response.get_json()['code'], 'physical_delete_requires_verified_upload')
                        self.assertIsNotNone(ProjectFile.query.get(file_id))
                        self.assertEqual(outside.read_text(), 'synthetic outside sentinel')
                        self.assertEqual(unrelated.read_text(), 'synthetic unrelated upload')

    def test_project_attachment_detach_with_string_jwt_keeps_uploaded_bytes(self):
        from app.models.project import Project, ProjectFile
        owner = self.make_user()
        self.make_user(email='other@example.com', username='other')
        project = Project(name='Owner project', creator_id=owner)
        self.db.session.add(project)
        self.db.session.commit()
        owner_headers = self.auth_headers(self.login_as()['access_token'])
        other_headers = self.auth_headers(self.login_as('other@example.com')['access_token'])
        with tempfile.TemporaryDirectory(prefix='auth-upload-detach-') as directory:
            uploaded = Path(directory) / 'fixture.txt'
            uploaded.write_text('synthetic uploaded bytes')
            with mock.patch.dict(self.app.config, {'UPLOAD_FOLDER': directory}):
                attached = self.client.post(f'/api/v1/projects/{project.id}/files',
                    headers=owner_headers, json={'file_path': uploaded.name, 'original_name': 'fixture.txt'})
                self.assertEqual(attached.status_code, 201)
                file_id = attached.get_json()['id']
                path = f'/api/v1/projects/{project.id}/files/{file_id}'
                self.assertEqual(self.client.delete(path, headers=other_headers).status_code, 403)
                self.assertEqual(self.client.delete(path + '/physical', headers=other_headers).status_code, 403)
                self.assertEqual(self.client.delete(path + '/physical').status_code, 401)
                self.assertIsNotNone(ProjectFile.query.get(file_id))
                self.assertEqual(self.client.delete(path, headers=owner_headers).status_code, 200)
                self.assertIsNone(ProjectFile.query.get(file_id))
                self.assertEqual(uploaded.read_text(), 'synthetic uploaded bytes')


    def test_session_migration_preserves_existing_accounts(self):
        import importlib.util
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from app.models import AuthSession, User
        user_id = self.make_user('Administrator')
        AuthSession.__table__.drop(self.db.engine)
        path = BACKEND_ROOT / 'migrations/versions/a20261020_auth_sessions.py'
        spec = importlib.util.spec_from_file_location('auth_migration', path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        with self.db.engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
        self.assertEqual(User.query.get(user_id).role.name, 'Administrator')
        self.assertIn('access_token', self.login_as())

    def test_explicit_admin_bootstrap_has_no_default_password(self):
        runner = self.app.test_cli_runner()
        response = runner.invoke(args=['create-admin', '--email', 'root@example.test', '--username', 'root'],
                                 input='FixtureSecret123!\nFixtureSecret123!\n')
        self.assertEqual(response.exit_code, 0, response.output)
        login = self.client.post('/api/v1/auth/login', json={
            'email': 'root@example.test', 'password': 'FixtureSecret123!',
        })
        self.assertEqual(login.get_json()['user']['role'], 'Administrator')


if __name__ == '__main__':
    unittest.main()
