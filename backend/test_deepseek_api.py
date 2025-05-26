#!/usr/bin/env python3
"""
测试DeepSeek API的脚本
"""

import requests
import json

def test_deepseek_api():
    """测试DeepSeek API"""
    base_url = "http://localhost:5003"
    
    # 测试RAG聊天
    print("🧪 测试DeepSeek API...")
    
    test_data = {
        "query": "什么是机器学习？",
        "provider": "deepseek"
    }
    
    try:
        response = requests.post(f"{base_url}/api/v1/rag/chat", json=test_data, timeout=30)
        
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ DeepSeek API 测试成功!")
                print(f"模型: {result['data'].get('model', '未知')}")
                print(f"检索文档数: {result['data'].get('retrieved_docs', 0)}")
                print(f"回答长度: {len(result['data'].get('answer', ''))}")
                print(f"回答预览: {result['data'].get('answer', '')[:100]}...")
            else:
                print(f"❌ API返回错误: {result.get('message', '未知错误')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时 - 这可能是正常的，因为DeepSeek API可能需要较长时间")
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

if __name__ == '__main__':
    test_deepseek_api() 