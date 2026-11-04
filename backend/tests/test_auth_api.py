import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = Path(tempfile.mkdtemp(prefix='auth-api-tests-'))

def build_stub_modules():
    flashrag_module = types.ModuleType('app.utils.flashrag_service')
    flashrag_module.flashrag_service = types.SimpleNamespace(
        rag_query=lambda *args, **kwargs: {
            'success': True,
            'data': {
                'answer': 'stubbed answer',
                'sources': [],
                'model': 'stubbed-model',
            },
        },
        _init_index=lambda: None,
    )

    llm_api_module = types.ModuleType('app.utils.llm_api')
    llm_api_module.llm_service = types.SimpleNamespace(
        summarize_url=lambda *args, **kwargs: {
            'success': True,
            'data': {
                'summary': 'stubbed summary',
                'title': 'stubbed title',
                'tags': '',
            },
        }
    )

    chat_with_doc_module = types.ModuleType('app.utils.chat_with_doc')
    chat_with_doc_module.chat_with_document = lambda *args, **kwargs: {
        'answer': 'stubbed document answer',
        'provider': 'stubbed',
    }
    chat_with_doc_module.chat_with_knowledge_base = lambda *args, **kwargs: {
        'answer': 'stubbed kb answer',
        'provider': 'stubbed',
    }

    return {
        'app.utils.flashrag_service': flashrag_module,
        'app.utils.llm_api': llm_api_module,
        'app.utils.chat_with_doc': chat_with_doc_module,
    }


class TestAuthAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module_patcher = mock.patch.dict(sys.modules, build_stub_modules())
        cls.module_patcher.start()

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
        cls.module_patcher.stop()
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

        response = self.login_user(password='wrong-password')

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


if __name__ == '__main__':
    unittest.main()
