# 模拟数据文件，用于测试和开发

# 模拟技术总结数据
MOCK_TECH_SUMMARIES = [
    {
        "id": 1,
        "title": "Flask Web开发入门",
        "content": "Flask是一个轻量级的Python Web框架，易于学习和使用...",
        "created_at": "2023-01-01",
        "author": "测试用户"
    },
    {
        "id": 2,
        "title": "Vue.js组件化开发",
        "content": "Vue.js是一个渐进式JavaScript框架，适用于构建用户界面...",
        "created_at": "2023-02-01",
        "author": "测试用户"
    }
]

# 模拟聊天响应数据
def get_mock_chat_response(query, provider="deepseek"):
    "生成模拟聊天响应
    
    Args:
        query: 用户查询
        provider: 服务提供商
        
    Returns:
        模拟响应字典
    "
    return {
        "answer": f"这是对问题 '{query}' 的模拟回答",
        "source": "模拟数据",
        "provider": provider
    }
