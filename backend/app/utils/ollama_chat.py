import logging
import time
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

class OllamaChat:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen:7b-q4_0"  # 默认使用通义千问模型
        
    def chat(self, query: str) -> Dict[str, Any]:
        """
        与Ollama进行对话
        
        Args:
            query: 用户问题
            
        Returns:
            Dict包含success和data字段
        """
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
                error_msg = f"Ollama API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
                
        except Exception as e:
            error_msg = f"与Ollama对话时出错: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg
            } 