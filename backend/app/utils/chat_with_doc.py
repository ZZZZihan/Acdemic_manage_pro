import logging
import os
import requests
from typing import Dict, Any, Optional, List
from app.utils.knowledge_base import knowledge_base
from app.utils.flashrag_service import flashrag_service

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def chat_with_document(document_content: str, user_query: str, provider: str = 'deepseek') -> Dict[str, Any]:
    """
    基于单个文档内容回答用户问题
    
    Args:
        document_content: 文档内容
        user_query: 用户问题
        provider: 使用的AI提供商，默认为deepseek
        
    Returns:
        包含回答的字典
    """
    logger.info(f"使用{provider}基于单个文档进行问答，问题: {user_query}")
    
    try:
        # 获取API密钥
        DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        
        # 检查是否有可用的API密钥
        if provider.lower() == 'deepseek' and not DEEPSEEK_API_KEY:
            return {
                "success": False,
                "message": "未设置DeepSeek API密钥，无法使用DeepSeek功能",
                "provider": provider
            }
        elif provider.lower() == 'openai' and not OPENAI_API_KEY:
            return {
                "success": False,
                "message": "未设置OpenAI API密钥，无法使用OpenAI功能",
                "provider": provider
            }
        
        # 构建系统提示
        system_prompt = f"""你是一个智能问答助手。请基于以下文档内容回答用户的问题。
如果文档中没有相关信息，请诚实地说不知道，不要编造答案。

文档内容:
{document_content}
"""
        
        # 根据不同提供商调用相应API
        if provider.lower() == 'deepseek':
            api_url = "https://api.deepseek.com/v1/chat/completions"
            api_key = DEEPSEEK_API_KEY
            model = "deepseek-chat"
        else:  # openai
            api_url = "https://api.openai.com/v1/chat/completions"
            api_key = OPENAI_API_KEY
            model = "gpt-3.5-turbo"
        
        # 准备请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            "temperature": 0.7
        }
        
        # 发送请求
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        # 解析响应
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            
            return {
                "success": True,
                "answer": answer,
                "provider": provider
            }
        else:
            error_msg = f"API调用失败: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "provider": provider
            }
    
    except Exception as e:
        error_msg = f"处理查询时出错: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "provider": provider
        }

def chat_with_knowledge_base(user_query: str, doc_id: Optional[str] = None, provider: str = 'deepseek') -> Dict[str, Any]:
    """
    基于知识库回答用户问题
    
    Args:
        user_query: 用户问题
        doc_id: 文档ID，如果提供则只在该文档中搜索
        provider: 使用的AI提供商，默认为deepseek
        
    Returns:
        包含回答的字典
    """
    logger.info(f"使用{provider}基于知识库进行问答，问题: {user_query}，文档ID: {doc_id}")
    
    try:
        # 如果指定了文档ID，则只在该文档中搜索
        if doc_id:
            document = knowledge_base.get_document(doc_id)
            if not document:
                return {
                    "success": False,
                    "message": f"文档ID {doc_id} 不存在于知识库中",
                    "provider": provider
                }
            
            # 使用单个文档内容回答问题
            return chat_with_document(document['content'], user_query, provider)
        
        # 否则，使用FlashRAG服务执行完整的RAG查询
        try:
            result = flashrag_service.rag_query(user_query, provider)
            return result
        except Exception as e:
            error_msg = f"使用FlashRAG服务查询失败: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "provider": provider
            }
    
    except Exception as e:
        error_msg = f"处理知识库查询时出错: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "provider": provider
        }