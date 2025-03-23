import logging
import random
import time
from typing import Dict, Any, Optional, List

from app.utils.knowledge_base import knowledge_base

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
    
    # 模拟处理延迟
    if provider.lower() == 'deepseek':
        delay = random.uniform(1.5, 3)
    else:  # openai
        delay = random.uniform(0.8, 1.5)
        
    time.sleep(delay)
    
    # 简单的关键词匹配
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
        answer = f"## 回答\n\n根据文档内容，关于\"{user_query}\"的信息如下：\n\n"
        
        # 添加找到的相关内容
        for i, sentence in enumerate(relevant_sentences[:3]):  # 最多使用3个相关段落
            answer += f"{sentence}\n\n"
            
        # 添加一些通用的结束语
        answer += "希望这些信息对您有所帮助。如果您有更多问题，请继续提问。"
    else:
        answer = f"## 抱歉\n\n在提供的文档中没有找到与\"{user_query}\"直接相关的信息。请尝试使用其他关键词，或者提出与文档内容更相关的问题。"
    
    return {
        "success": True,
        "answer": answer,
        "provider": f"mock_{provider}"
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
    
    # 模拟处理延迟
    if provider.lower() == 'deepseek':
        delay = random.uniform(1.5, 3)
    else:  # openai
        delay = random.uniform(0.8, 1.5)
        
    time.sleep(delay)
    
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
    # 简单的关键词匹配
    keywords = user_query.lower().split()
    relevant_documents = []
    
    # 在所有文档中搜索
    for doc_id, doc in knowledge_base.get_all_documents().items():
        doc_content = doc['content'].lower()
        doc_title = doc['title'].lower()
        
        # 计算关键词匹配度
        match_score = 0
        for keyword in keywords:
            if keyword in doc_title:
                match_score += 2  # 标题匹配权重更高
            if keyword in doc_content:
                match_score += 1
        
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
        
        answer = f"## 回答\n\n根据知识库内容，关于\"{user_query}\"的信息如下：\n\n"
        
        # 从每个文档中提取相关段落
        for doc in top_documents:
            # 将文档分成段落
            paragraphs = doc['content'].split('\n\n')
            
            # 在段落中查找包含关键词的内容
            relevant_paragraphs = []
            for paragraph in paragraphs:
                paragraph_lower = paragraph.lower()
                if any(keyword in paragraph_lower for keyword in keywords):
                    relevant_paragraphs.append(paragraph)
            
            # 最多使用每个文档中的2个最相关段落
            if relevant_paragraphs:
                answer += f"### 来自《{doc['title']}》的内容：\n\n"
                for paragraph in relevant_paragraphs[:2]:
                    answer += f"{paragraph}\n\n"
        
        # 添加一些通用的结束语
        answer += "希望这些信息对您有所帮助。如果您有更多问题，请继续提问。"
    else:
        answer = f"## 抱歉\n\n在知识库中没有找到与\"{user_query}\"直接相关的信息。请尝试使用其他关键词，或者提出更具体的问题。"
    
    return {
        "success": True,
        "answer": answer,
        "provider": f"mock_{provider}"
    }