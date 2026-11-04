"""测试与开发阶段使用的模拟数据。"""

from __future__ import annotations


MOCK_TECH_SUMMARIES = [
    {
        'id': 1,
        'title': 'Flask Web开发入门',
        'content': 'Flask是一个轻量级的Python Web框架，易于学习和使用。',
        'created_at': '2023-01-01',
        'author': '测试用户',
    },
    {
        'id': 2,
        'title': 'Vue.js组件化开发',
        'content': 'Vue.js是一个渐进式JavaScript框架，适用于构建用户界面。',
        'created_at': '2023-02-01',
        'author': '测试用户',
    },
]


def get_mock_chat_response(query: str, provider: str = 'deepseek') -> dict[str, str]:
    """根据问题生成稳定的模拟问答响应。"""

    return {
        'answer': f"这是对问题 '{query}' 的模拟回答",
        'source': '模拟数据',
        'provider': provider,
    }
