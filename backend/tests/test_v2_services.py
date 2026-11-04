import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app_v2.mcp.registry import build_registry
from app_v2.providers import build_execution_chain, build_provider_registry


class TestProviderRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = build_provider_registry()

    def test_provider_tiers_match_product_contract(self):
        self.assertEqual(self.registry.get('openai').tier, 'A')
        self.assertEqual(self.registry.get('claude').tier, 'A')
        self.assertEqual(self.registry.get('deepseek').tier, 'B')
        self.assertEqual(self.registry.get('minimax').tier, 'B')
        self.assertEqual(self.registry.get('ollama').tier, 'C')

    def test_ollama_is_local_only_fallback(self):
        profile = self.registry.get('ollama')

        self.assertTrue(profile.local_only)
        self.assertFalse(profile.supports_external_write)
        self.assertFalse(profile.supports_google_connectors)

    def test_adapters_expose_provider_specific_payload_shapes(self):
        messages = [
            {'role': 'user', 'content': '安排下周项目评审'},
        ]
        tools = [
            {'name': 'calendar.create_event', 'description': 'Create an event'},
        ]

        openai_payload = self.registry.get_adapter('openai').build_payload(messages, tools)
        claude_payload = self.registry.get_adapter('claude').build_payload(messages, tools)
        deepseek_payload = self.registry.get_adapter('deepseek').build_payload(messages, tools)
        minimax_payload = self.registry.get_adapter('minimax').build_payload(messages, tools)
        ollama_payload = self.registry.get_adapter('ollama').build_payload(messages, tools)

        self.assertIn('input', openai_payload)
        self.assertIn('tools', openai_payload)
        self.assertIn('messages', claude_payload)
        self.assertIn('tools', claude_payload)
        self.assertIn('messages', deepseek_payload)
        self.assertIn('tools', deepseek_payload)
        self.assertIn('messages', minimax_payload)
        self.assertIn('tools', minimax_payload)
        self.assertIn('messages', ollama_payload)
        self.assertIn('format', ollama_payload)


class TestMcpRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = build_registry()

    def test_registry_exposes_tools_resources_and_prompts(self):
        manifest = self.registry.manifest()

        self.assertIn('task.create', [tool['name'] for tool in manifest['tools']])
        self.assertIn('calendar.create_event', [tool['name'] for tool in manifest['tools']])
        self.assertIn('lab://users/me', [resource['uri'] for resource in manifest['resources']])
        self.assertIn('meeting.plan', [prompt['name'] for prompt in manifest['prompts']])

    def test_external_write_tools_require_approval(self):
        calendar_tool = self.registry.get_tool('calendar.create_event')
        task_tool = self.registry.get_tool('task.create')

        self.assertTrue(calendar_tool.requires_approval)
        self.assertFalse(task_tool.requires_approval)


class TestProviderRouting(unittest.TestCase):
    def setUp(self):
        self.registry = build_provider_registry()

    def test_external_write_routes_tier_b_to_tier_a(self):
        chain = build_execution_chain(
            requested_provider='deepseek',
            registry=self.registry,
            requires_external_write=True,
            lock_to_requested=False,
        )
        self.assertEqual(chain[0], 'openai')
        self.assertIn('claude', chain)
        self.assertIn('deepseek', chain)

    def test_local_lock_keeps_ollama_first(self):
        chain = build_execution_chain(
            requested_provider='ollama',
            registry=self.registry,
            requires_external_write=True,
            lock_to_requested=True,
        )
        self.assertEqual(chain[0], 'ollama')


if __name__ == '__main__':
    unittest.main()
