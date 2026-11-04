import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.mock_data import MOCK_TECH_SUMMARIES, get_mock_chat_response

class TestMockData(unittest.TestCase):
    def test_mock_tech_summaries(self):
        """测试模拟技术总结数据"""
        self.assertTrue(len(MOCK_TECH_SUMMARIES) > 0)
        self.assertEqual(MOCK_TECH_SUMMARIES[0]["id"], 1)
        self.assertIn("title", MOCK_TECH_SUMMARIES[0])

    def test_mock_chat_response(self):
        """测试模拟聊天响应"""
        response = get_mock_chat_response("测试问题")
        self.assertIn("answer", response)
        self.assertIn("测试问题", response["answer"])
        self.assertEqual(response["source"], "模拟数据")
        self.assertEqual(response["provider"], "deepseek")

    def test_mock_chat_response_uses_custom_provider(self):
        """测试模拟聊天响应支持自定义服务商"""
        response = get_mock_chat_response("测试问题", provider="openai")
        self.assertEqual(response["provider"], "openai")
