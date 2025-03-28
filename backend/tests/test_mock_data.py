import unittest
from app.utils.mock_data import MOCK_TECH_SUMMARIES, get_mock_chat_response

class TestMockData(unittest.TestCase):
    def test_mock_tech_summaries(self):
        """测试模拟技术总结数据"""
        self.assertTrue(len(MOCK_TECH_SUMMARIES) > 0)
        self.assertEqual(MOCK_TECH_SUMMARIES[0]["id"], 1)

    def test_mock_chat_response(self):
        """测试模拟聊天响应"""
        response = get_mock_chat_response("测试问题")
        self.assertIn("answer", response)
        self.assertEqual(response["provider"], "deepseek")
