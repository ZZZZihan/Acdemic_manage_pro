import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app_v2.main import create_app


class TestV2Authentication(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app('sqlite+pysqlite:///' + str(Path(self.temp.name) / 'v2.sqlite'), testing=True)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.state.engine.dispose()
        self.temp.cleanup()

    def test_health_is_public_but_workspace_and_mcp_are_not(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        for path in ['/api/v2/providers', '/api/v2/approvals', '/mcp']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post('/api/v2/chat/threads', json={'title': 'private'}).status_code, 401)
        self.assertEqual(self.client.post('/mcp/tools/call', json={'name': 'task.create', 'arguments': {}}).status_code, 401)

    def test_valid_session_is_checked_with_identity_service(self):
        with patch('app_v2.auth.urlopen') as call:
            call.return_value.__enter__.return_value.read.return_value = json.dumps({'id': 1, 'role': 'User'}).encode()
            response = self.client.get('/api/v2/providers', headers={'Authorization': 'Bearer test-access'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(call.call_args.args[0].get_header('Authorization'), 'Bearer test-access')

    def test_expired_or_revoked_jwt_code_is_preserved_for_frontend(self):
        for code in ['token_expired', 'session_revoked']:
            body = io.BytesIO(json.dumps({'code': code, 'message': 'expired'}).encode())
            with patch('app_v2.auth.urlopen', side_effect=HTTPError('http://identity', 401, 'Unauthorized', {}, body)):
                response = self.client.get('/api/v2/providers', headers={'Authorization': 'Bearer invalid'})
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()['code'], code)

    def test_identity_service_outage_fails_closed(self):
        with patch('app_v2.auth.urlopen', side_effect=URLError('offline')):
            response = self.client.get('/api/v2/providers', headers={'Authorization': 'Bearer any'})
            self.assertEqual(response.status_code, 503)
