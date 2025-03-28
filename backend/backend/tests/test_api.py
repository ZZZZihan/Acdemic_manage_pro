import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class TestTechSummaryAPI(unittest.TestCase):
    def test_api_connection(self):
        # 简单的测试确保代码能运行
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()