import logging
import time
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OllamaChat:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen:7b-q4_0"  # 默认使用通义千问模型
        
    def chat(self, query: str, use_mock: bool = True) -> Dict[str, Any]:
        """
        与Ollama进行对话
        
        Args:
            query: 用户问题
            use_mock: 是否使用模拟模式
            
        Returns:
            Dict包含success和data字段
        """
        if use_mock:
            # 模拟模式直接返回结果，不需要调用Ollama
            return self._mock_chat(query)
            
        try:
            # 构建请求数据
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的AI助手，请用简洁专业的语言回答问题。"
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "stream": False
            }
            
            # 发送请求到Ollama API
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "data": {
                        "answer": result.get("message", {}).get("content", ""),
                        "model": self.model
                    }
                }
            else:
                logger.error(f"Ollama API请求失败: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Ollama API请求失败: {response.status_code}"
                }
                
        except Exception as e:
            logger.exception(f"与Ollama对话时出错: {str(e)}")
            return {
                "success": False,
                "message": f"与Ollama对话时出错: {str(e)}"
            }
            
    def _mock_chat(self, query: str) -> Dict[str, Any]:
        """
        模拟Ollama对话响应
        
        Args:
            query: 用户问题
            
        Returns:
            Dict包含模拟的回答
        """
        # 模拟处理延迟
        time.sleep(1.5)
        
        # 简单的关键词匹配
        keywords = {
            "你好": "你好！我是AI助手，很高兴为您服务。",
            "你是谁": "我是基于Ollama的AI助手，可以帮助您解答问题。",
            "帮助": "我可以帮您解答问题、分析数据、编写代码等。请告诉我您需要什么帮助。",
            "谢谢": "不客气！如果还有其他问题，随时问我。",
            "再见": "再见！祝您使用愉快！",
            "测试": "测试成功！模拟模式正常工作中。",
            "ollama": "Ollama是一个开源的大语言模型运行框架，可以让您在本地运行各种开源大模型，如Llama 2、Mistral和Vicuna等。"
        }
        
        # 查找匹配的关键词
        for keyword, response in keywords.items():
            if keyword in query:
                return {
                    "success": True,
                    "data": {
                        "answer": response,
                        "model": "mock模式"
                    }
                }
        
        # 如果没有匹配的关键词，返回默认回答
        return {
            "success": True,
            "data": {
                "answer": "我收到了您的问题：\"{}\"。这是一个模拟回答，实际部署时将连接到Ollama服务获取真实回答。".format(query),
                "model": "mock模式"
            }
        } 