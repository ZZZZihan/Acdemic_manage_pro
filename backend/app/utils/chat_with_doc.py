import logging
import random
import time
import requests
import json
import os
from typing import Dict, Any, Optional, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.utils.knowledge_base import knowledge_base

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置选项
USE_FALLBACK_FIRST = os.environ.get("USE_FALLBACK_FIRST", "false").lower() == "true"  # 是否优先使用后备方案

# LLM API配置
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 超时配置
API_CONNECT_TIMEOUT = int(os.environ.get("API_CONNECT_TIMEOUT", "10"))
API_READ_TIMEOUT = int(os.environ.get("API_READ_TIMEOUT", "90"))
API_MAX_RETRIES = int(os.environ.get("API_MAX_RETRIES", "3"))

# 创建会话对象以复用连接
def create_session():
    """创建带有重试策略的会话"""
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        backoff_factor=1
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# 全局会话对象
_session = create_session()

def _call_ai_api(query: str, system_prompt: str, provider: str = 'deepseek') -> str:
    """
    调用AI API生成回答
    
    Args:
        query: 用户查询
        system_prompt: 系统提示
        provider: AI提供商
        
    Returns:
        AI生成的回答
    """
    max_retries = API_MAX_RETRIES
    retry_delay = 2  # 秒
    
    for attempt in range(max_retries):
        try:
            if provider == "deepseek" and DEEPSEEK_API_KEY:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Connection": "close"  # 避免连接复用问题
                }
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500,  # 进一步减少token数量以提高响应速度
                    "stream": False  # 确保不使用流式响应
                }
                
                # 分别设置连接超时和读取超时
                timeout_config = (API_CONNECT_TIMEOUT, API_READ_TIMEOUT)  # (连接超时, 读取超时)
                
                logger.info(f"正在调用DeepSeek API (尝试 {attempt + 1}/{max_retries})...")
                
                response = _session.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout_config,
                    verify=True  # 确保SSL验证
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("DeepSeek API调用成功")
                    return result['choices'][0]['message']['content']
                else:
                    logger.error("DeepSeek API请求失败: status=%s", response.status_code)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))  # 递增延迟
                        continue
                    
            elif provider == "openai" and OPENAI_API_KEY:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Connection": "close"
                }
                
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1500,
                    "stream": False
                }
                
                timeout_config = (API_CONNECT_TIMEOUT, API_READ_TIMEOUT)
                
                logger.info(f"正在调用OpenAI API (尝试 {attempt + 1}/{max_retries})...")
                
                response = _session.post(
                    OPENAI_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=timeout_config,
                    verify=True
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("OpenAI API调用成功")
                    return result['choices'][0]['message']['content']
                else:
                    logger.error("OpenAI API请求失败: status=%s", response.status_code)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                        
        except requests.exceptions.Timeout as e:
            logger.warning(f"调用{provider} API超时 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"调用{provider} API连接错误 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
        except Exception as e:
            logger.exception(f"调用{provider} API时出错 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
    
    # 如果所有重试都失败，返回None
    logger.error("语言模型调用失败，已拒绝生成无依据回答")
    return None

def _unavailable(provider, code, message, doc_ids=None, sources=None):
    return {
        "success": False,
        "code": code,
        "message": message,
        "provider": provider,
        "retrieved_doc_ids": doc_ids or [],
        "sources": sources or [],
    }


def chat_with_document(document_content: str, user_query: str, provider: str = "deepseek") -> Dict[str, Any]:
    """Answer from one document, or refuse when generation is unavailable."""
    from app.rag.service import LLM_UNAVAILABLE_MESSAGE, NO_GROUNDED_MESSAGE

    logger.info("document chat provider=%s", provider)
    if not (document_content or "").strip():
        return _unavailable(provider, "no_grounded_answer", NO_GROUNDED_MESSAGE)

    system_prompt = (
        "你是实验室知识库问答助手。只根据给定文档回答。"
        "文档没有依据时直接说明不知道，不要编造。\n\n"
        f"文档内容：\n{document_content}"
    )
    answer = _call_ai_api(user_query, system_prompt, provider)
    if not answer:
        return _unavailable(provider, "llm_unavailable", LLM_UNAVAILABLE_MESSAGE)
    return {
        "success": True,
        "answer": answer,
        "provider": provider,
        "retrieved_doc_ids": [],
        "sources": [],
    }


def chat_with_knowledge_base(user_query: str, doc_id: Optional[str] = None, provider: str = "deepseek") -> Dict[str, Any]:
    """Answer from the in-memory corpus. No hit and missing model are explicit."""
    from app.rag.service import LLM_UNAVAILABLE_MESSAGE, NO_GROUNDED_MESSAGE

    logger.info("knowledge chat provider=%s scoped=%s", provider, bool(doc_id))
    from flask import g, has_request_context

    from app.rag.acl import can_read

    viewer = g.actor if has_request_context() else None
    if doc_id:
        document = knowledge_base.get_document(doc_id)
        metadata = (document or {}).get("metadata") or {}
        if not document or not can_read(metadata.get("access_scope"), metadata.get("user_id"), viewer):
            return _unavailable(provider, "no_grounded_answer", NO_GROUNDED_MESSAGE)
        result = chat_with_document(document.get("content") or "", user_query, provider)
        result["retrieved_doc_ids"] = [str(doc_id)]
        result["sources"] = [{
            "id": str(doc_id),
            "title": document.get("title") or "",
        }]
        return result

    matches = []
    for match in knowledge_base.search_documents(user_query):
        metadata = match.get("metadata") or {}
        if can_read(metadata.get("access_scope"), metadata.get("user_id"), viewer):
            matches.append(match)
        if len(matches) >= 3:
            break
    sources = [{
        "id": match["id"],
        "title": match.get("title") or "",
    } for match in matches]
    doc_ids = [match["id"] for match in matches]
    if not matches:
        return _unavailable(provider, "no_grounded_answer", NO_GROUNDED_MESSAGE)

    context = "\n\n".join(
        f"文档 {match['id']}（{match.get('title') or '未命名'}）:\n{(match.get('content') or '')[:2000]}"
        for match in matches
    )
    system_prompt = (
        "你是实验室知识库问答助手。只根据给定文档回答。"
        "文档没有依据时直接说明不知道，不要编造。\n\n"
        f"{context}"
    )
    answer = _call_ai_api(user_query, system_prompt, provider)
    if not answer:
        return _unavailable(provider, "llm_unavailable", LLM_UNAVAILABLE_MESSAGE, doc_ids, sources)
    return {
        "success": True,
        "answer": answer,
        "provider": provider,
        "retrieved_doc_ids": doc_ids,
        "sources": sources,
    }
