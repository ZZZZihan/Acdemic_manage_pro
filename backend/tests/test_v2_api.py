import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app_v2.main import create_app


class TestV2Api(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix='app-v2-tests-')
        database_url = f"sqlite+pysqlite:///{Path(self.temp_dir.name) / 'app_v2.sqlite'}"
        self.app = create_app(database_url=database_url, testing=True)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_provider_directory_lists_all_supported_backends(self):
        response = self.client.get('/api/v2/providers')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            [provider['name'] for provider in payload['providers']],
            ['openai', 'claude', 'deepseek', 'minimax', 'ollama'],
        )

    def test_health_endpoint_reports_v2_service(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertEqual(payload['version'], '2.0.0')

    def test_interview_architecture_endpoint_exposes_core_highlights(self):
        response = self.client.get('/api/v2/interview/architecture')
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['project_version'], '2.0.0')
        self.assertIn('dual_core_orchestration', payload['highlights'])
        self.assertIn('mcp_capability_plane', payload['highlights'])
        self.assertIn('provider_routing_trace', payload['highlights'])

    def test_chat_message_can_create_pending_approval(self):
        thread_response = self.client.post('/api/v2/chat/threads', json={'title': '项目助手'})
        thread_id = thread_response.json()['thread']['id']

        response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': 'openai',
                'content': '请安排下周二下午三点的项目评审会议，并通知大家。',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['assistant']['provider'], 'openai')
        self.assertTrue(payload['approval_requested'])
        self.assertEqual(payload['approval']['tool_name'], 'calendar.create_event')
        self.assertEqual(payload['routing']['requested_provider'], 'openai')
        self.assertEqual(payload['routing']['resolved_provider'], 'openai')

        approvals_response = self.client.get('/api/v2/approvals')
        self.assertEqual(approvals_response.status_code, 200)
        self.assertEqual(len(approvals_response.json()['items']), 1)

    def test_deepseek_request_escalates_to_tier_a_for_external_write(self):
        thread_id = self.client.post('/api/v2/chat/threads', json={'title': '升级路由测试'}).json()['thread']['id']
        response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': 'deepseek',
                'content': '请在 Google Calendar 创建一个明天下午两点的项目评审会议。',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['routing']['requested_provider'], 'deepseek')
        self.assertEqual(payload['routing']['resolved_provider'], 'openai')
        self.assertTrue(payload['routing']['requires_external_write'])
        self.assertGreaterEqual(len(payload['routing']['trace']), 2)

    def test_approval_decision_updates_state_and_generates_activity(self):
        thread_id = self.client.post('/api/v2/chat/threads', json={'title': '审批测试'}).json()['thread']['id']
        message_response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': 'claude',
                'content': '帮我在 Google Calendar 里创建一个明天上午十点的组会。',
            },
        )
        approval_id = message_response.json()['approval']['id']

        decision_response = self.client.post(
            f'/api/v2/approvals/{approval_id}/decision',
            json={'decision': 'approved'},
        )

        self.assertEqual(decision_response.status_code, 200)
        payload = decision_response.json()
        self.assertEqual(payload['approval']['status'], 'approved')
        self.assertIsNotNone(payload['approval']['decided_at'])
        self.assertEqual(payload['activity']['event_type'], 'approval.approved')

    def test_invalid_provider_returns_bad_request(self):
        thread_id = self.client.post('/api/v2/chat/threads', json={'title': 'provider错误'}).json()['thread']['id']
        response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': 'unknown-provider',
                'content': '测试无效 provider',
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_blank_provider_is_rejected_by_request_schema(self):
        thread_id = self.client.post('/api/v2/chat/threads', json={'title': 'provider校验'}).json()['thread']['id']
        response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': '   ',
                'content': '测试空 provider',
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_knowledge_asset_ingest_and_search_tool(self):
        ingest_response = self.client.post(
            '/api/v2/knowledge/assets',
            json={
                'title': 'MCP 设计笔记',
                'content': '内部工具需要区分 tools resources prompts 三类能力。',
                'source_type': 'note',
                'tags': ['mcp', 'architecture'],
            },
        )
        self.assertEqual(ingest_response.status_code, 201)

        search_response = self.client.post(
            '/mcp/tools/call',
            json={
                'name': 'knowledge.search',
                'arguments': {'query': 'resources prompts', 'limit': 5},
            },
        )

        self.assertEqual(search_response.status_code, 200)
        payload = search_response.json()
        self.assertEqual(payload['result']['items'][0]['title'], 'MCP 设计笔记')

    def test_task_intent_creates_internal_task_tool_call(self):
        thread_id = self.client.post('/api/v2/chat/threads', json={'title': '任务测试'}).json()['thread']['id']
        response = self.client.post(
            '/api/v2/chat/messages',
            json={
                'thread_id': thread_id,
                'provider': 'claude',
                'content': '请把本周项目推进事项整理成任务列表。',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload['approval_requested'])
        self.assertEqual(payload['tool_calls'][0]['tool'], 'task.create')
        self.assertIn('task', payload['tool_calls'][0]['result'])

    def test_mcp_directory_and_resource_reads_work(self):
        manifest_response = self.client.get('/mcp')
        self.assertEqual(manifest_response.status_code, 200)
        manifest = manifest_response.json()
        self.assertIn('tools', manifest)
        self.assertIn('resources', manifest)
        self.assertIn('prompts', manifest)

        resource_response = self.client.post('/mcp/resources/read', json={'uri': 'lab://users/me'})
        self.assertEqual(resource_response.status_code, 200)
        payload = resource_response.json()
        self.assertEqual(payload['resource']['uri'], 'lab://users/me')
        self.assertIn('display_name', payload['contents'])


if __name__ == '__main__':
    unittest.main()
