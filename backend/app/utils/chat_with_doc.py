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
                    logger.error(f"DeepSeek API请求失败: {response.status_code}, 响应: {response.text}")
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
                    logger.error(f"OpenAI API请求失败: {response.status_code}, 响应: {response.text}")
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
    logger.error(f"所有{max_retries}次API调用尝试都失败，将使用后备方案")
    return None

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
    
    # 构建系统提示
    system_prompt = f"""你是一个助手。请基于以下文档内容回答用户的问题。如果文档中没有相关信息，请说'文档中没有找到相关信息'。

文档内容：
{document_content}

请用中文回答，要准确、详细、全面。请提供完整的解释和具体的步骤，包括：
1. 详细的概念解释
2. 具体的实施步骤或方法
3. 相关的技术细节
4. 实际应用场景或示例
5. 注意事项或最佳实践

回答应该具有教学性质，帮助用户深入理解相关内容。"""
    
    # 尝试调用真实的AI API
    ai_answer = _call_ai_api(user_query, system_prompt, provider)
    
    if ai_answer:
        # 使用AI生成的回答
        answer = ai_answer
        provider_name = provider
    else:
        # 如果API调用失败，使用简单的关键词匹配作为后备
        logger.warning(f"AI API调用失败，使用后备方案")
        
        keywords = user_query.lower().split()
        relevant_sentences = []
        
        # 将文档分成段落
        paragraphs = document_content.split('\n\n')
        
        # 在段落中查找包含关键词的内容
        for paragraph in paragraphs:
            paragraph_lower = paragraph.lower()
            if any(keyword in paragraph_lower for keyword in keywords):
                relevant_sentences.append(paragraph)
        
        # 如果找到相关内容，生成回答
        if relevant_sentences:
            answer = f"根据文档内容，关于\"{user_query}\"的信息如下：\n\n"
            
            # 添加找到的相关内容
            for i, sentence in enumerate(relevant_sentences[:3]):  # 最多使用3个相关段落
                answer += f"{sentence}\n\n"
                
            answer += "\n### 深入学习建议\n\n"
            answer += "1. **仔细研读**：建议您详细阅读上述内容，理解每个要点\n"
            answer += "2. **实际操作**：尝试按照文档中的方法进行实践\n"
            answer += "3. **扩展阅读**：查找相关的补充资料和最新资讯\n"
            answer += "4. **记录总结**：将学到的知识整理成自己的笔记\n\n"
            answer += "如果您需要更详细的解释或有其他相关问题，请继续提问。"
        else:
            answer = f"""在提供的文档中没有找到与"{user_query}"直接相关的信息。

### 建议您可以尝试：

#### 1. 调整问题表达
- **使用文档中的关键词**：参考文档的标题和主要概念
- **更具体的问题**：针对文档的某个具体部分提问
- **相关概念查询**：询问与文档主题相关的概念

#### 2. 文档阅读策略
- **通读全文**：先整体了解文档的主要内容
- **重点标记**：标记出重要的概念和方法
- **分段理解**：逐段分析文档的核心信息

#### 3. 深入学习方法
- **实践验证**：尝试文档中提到的方法或技术
- **对比学习**：与其他相关资料进行对比
- **问题导向**：带着具体问题去阅读文档

如果您能提供更具体的问题或指出文档中您感兴趣的部分，我可以为您提供更有针对性的帮助。"""
        
        provider_name = f"fallback_{provider}"
    
    return {
        "success": True,
        "answer": answer,
        "provider": provider_name
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
    
    # 如果指定了文档ID，则只在该文档中搜索
    if doc_id:
        document = knowledge_base.get_document(doc_id)
        if not document:
            return {
                "success": False,
                "message": f"文档ID {doc_id} 不存在于知识库中",
                "provider": f"mock_{provider}"
            }
        
        # 使用单个文档内容回答问题
        return chat_with_document(document['content'], user_query, provider)
    
    # 否则，在整个知识库中搜索
    # 改进的关键词匹配
    query_lower = user_query.lower()
    keywords = user_query.lower().split()
    relevant_documents = []
    
    # 在所有文档中搜索
    for doc_id, doc in knowledge_base.get_all_documents().items():
        doc_content = doc['content'].lower()
        doc_title = doc['title'].lower()
        
        # 计算关键词匹配度
        match_score = 0
        
        # 检查完整查询是否在文档中
        if query_lower in doc_title:
            match_score += 5
        if query_lower in doc_content:
            match_score += 3
            
        # 检查单个关键词
        for keyword in keywords:
            if len(keyword) > 1:  # 忽略单字符关键词
                if keyword in doc_title:
                    match_score += 2  # 标题匹配权重更高
                if keyword in doc_content:
                    match_score += 1
        
        # 特殊处理一些技术术语
        tech_terms = ['rag', 'retrieval', 'augmented', 'generation', 'opencv', 'python', 'java', 'docker']
        for term in tech_terms:
            if term in query_lower and term in doc_content:
                match_score += 3
        
        if match_score > 0:
            relevant_documents.append({
                'id': doc_id,
                'title': doc['title'],
                'content': doc['content'],
                'match_score': match_score
            })
    
    # 按匹配度排序
    relevant_documents.sort(key=lambda x: x['match_score'], reverse=True)
    
    # 如果找到相关文档，生成回答
    if relevant_documents:
        # 最多使用前3个最相关的文档
        top_documents = relevant_documents[:3]
        
        # 构建上下文
        context_parts = []
        for doc in top_documents:
            context_parts.append(f"标题: {doc['title']}\n内容: {doc['content']}")
        
        context = "\n\n---\n\n".join(context_parts)
        
        # 构建系统提示
        system_prompt = f"""你是一个知识库助手。请基于以下知识库内容回答用户的问题。如果知识库中没有相关信息，请说'知识库中没有找到相关信息'。

知识库内容：
{context}

请用中文回答，要准确、详细、全面。请提供完整的解释和具体的步骤，包括：
1. 详细的概念解释
2. 具体的实施步骤或方法
3. 相关的技术细节
4. 实际应用场景或示例
5. 注意事项或最佳实践

回答应该具有教学性质，帮助用户深入理解相关内容。直接回答问题，不需要引用具体的文档编号。"""
        
        # 尝试调用真实的AI API
        ai_answer = _call_ai_api(user_query, system_prompt, provider)
        
        if ai_answer:
            # 使用AI生成的回答
            answer = ai_answer
            provider_name = provider
        else:
            # 如果API调用失败，使用后备方案
            logger.warning(f"AI API调用失败，使用后备方案")
            
            answer = f"根据知识库内容，关于\"{user_query}\"的信息如下：\n\n"
            
            # 从每个文档中提取相关段落
            for doc in top_documents:
                # 将文档分成段落
                paragraphs = doc['content'].split('\n\n')
                
                # 在段落中查找包含关键词的内容
                relevant_paragraphs = []
                for paragraph in paragraphs:
                    paragraph_lower = paragraph.lower()
                    # 检查完整查询或关键词
                    if (query_lower in paragraph_lower or 
                        any(keyword in paragraph_lower for keyword in keywords if len(keyword) > 1)):
                        relevant_paragraphs.append(paragraph)
                
                # 如果没有找到相关段落，使用文档的前几个段落
                if not relevant_paragraphs:
                    relevant_paragraphs = paragraphs[:2]
                
                # 最多使用每个文档中的2个最相关段落
                if relevant_paragraphs:
                    answer += f"### 来自《{doc['title']}》的内容：\n\n"
                    for paragraph in relevant_paragraphs[:2]:
                        if paragraph.strip():  # 确保段落不为空
                            answer += f"{paragraph}\n\n"
            
            # 添加一些通用的结束语
            answer += "\n### 学习建议\n\n"
            answer += "1. **深入理解**：建议您仔细阅读上述内容，理解核心概念\n"
            answer += "2. **实践应用**：尝试将理论知识应用到实际项目中\n"
            answer += "3. **持续学习**：关注相关技术的最新发展和最佳实践\n"
            answer += "4. **交流讨论**：与同事或社区成员分享经验和心得\n\n"
            answer += "如果您需要更详细的解释或有其他相关问题，请随时提问。"
            provider_name = f"fallback_{provider}"
    else:
        # 没有找到相关文档，提供通用的学习建议
        if any(keyword in user_query.lower() for keyword in ['java', 'python', 'javascript', '编程', '学习']):
            answer = f"""关于"{user_query}"，虽然知识库中没有找到直接相关的信息，但我可以为您提供一些通用的学习建议：

### 编程学习通用指南

#### 1. 基础知识建设
- **语法掌握**：熟练掌握编程语言的基本语法
- **数据结构**：理解数组、链表、栈、队列等基本数据结构
- **算法思维**：培养解决问题的逻辑思维能力
- **编程范式**：了解面向对象、函数式编程等不同范式

#### 2. 实践项目经验
- **小项目起步**：从简单的控制台程序开始
- **逐步进阶**：完成图形界面、Web应用等复杂项目
- **开源贡献**：参与开源项目，学习他人代码
- **个人作品集**：建立GitHub展示自己的项目

#### 3. 学习资源推荐
- **官方文档**：始终是最权威的学习资料
- **在线教程**：慕课网、B站、YouTube等平台
- **技术书籍**：经典教材和实战指南
- **技术社区**：Stack Overflow、CSDN、掘金等

#### 4. 最佳实践
- **代码规范**：遵循行业标准的编码规范
- **版本控制**：学会使用Git进行代码管理
- **测试驱动**：编写单元测试保证代码质量
- **持续学习**：关注技术发展趋势，不断更新知识

建议您可以尝试更具体的问题，或者查看知识库中的其他技术文档。"""
        else:
            answer = f"""在知识库中没有找到与"{user_query}"直接相关的信息。

### 建议您可以尝试：

#### 1. 调整搜索策略
- **使用更具体的关键词**：比如具体的技术名称、框架名称
- **尝试不同的表达方式**：用同义词或相关术语重新提问
- **分解复杂问题**：将复杂问题拆分成多个简单问题

#### 2. 浏览知识库内容
- **查看技术总结列表**：了解知识库中包含哪些技术文档
- **阅读相关文档**：寻找与您问题相关的技术文档
- **关注标签分类**：通过标签找到相关的技术领域

#### 3. 提问技巧
- **提供上下文**：说明您的具体使用场景
- **明确目标**：清楚表达您想要解决的问题
- **举例说明**：提供具体的例子或代码片段

#### 4. 其他学习资源
- **官方文档**：查阅相关技术的官方文档
- **技术社区**：在Stack Overflow、GitHub等平台寻求帮助
- **在线教程**：寻找相关的视频教程或博客文章

如果您有其他问题或需要特定技术的帮助，请随时提问。我会尽力为您提供有用的信息和建议。"""
        provider_name = f"fallback_{provider}"
    
    return {
        "success": True,
        "answer": answer,
        "provider": provider_name
    }