import logging
import json
import os
import numpy as np
import time
import hashlib
import faiss
from typing import Dict, List, Any, Optional
from sentence_transformers import SentenceTransformer
from .knowledge_base import knowledge_base

# 配置日志
logger = logging.getLogger(__name__)

class FlashRAGService:
    """
    FlashRAG服务类：基于中国人民大学NLPIR实验室开发的轻量高效RAG框架思路实现
    特点：高效轻量级、专注于检索和生成效率
    """
    
    def __init__(self):
        """初始化FlashRAG服务"""
        # 初始化知识库
        self.knowledge_base = knowledge_base
        
        # 初始化向量模型
        try:
            # 我们使用多语言模型以支持中英文
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"成功加载FlashRAG向量模型，维度: {self.dimension}")
        except Exception as e:
            logger.error(f"加载FlashRAG向量模型失败: {str(e)}")
            self.model = None
            self.dimension = 384  # 默认维度
            raise RuntimeError(f"加载FlashRAG向量模型失败，服务无法正常工作: {str(e)}")
        
        # 初始化FAISS索引
        self.index = None
        self.document_map = {}  # 存储ID到文档的映射
        self.cache = {}  # 查询缓存
        self.cache_size = 100  # 最大缓存条目数
        
        # 初始化向量索引
        self._init_index()
    
    def _init_index(self):
        """初始化FAISS索引"""
        try:
            # 创建FAISS索引（使用L2距离）
            self.index = faiss.IndexFlatL2(self.dimension)
            
            # 从知识库加载文档并索引
            documents = self.knowledge_base.get_all_documents()
            
            if documents:
                chunks = []
                doc_ids = []
                
                # 处理每个文档
                for doc_id, doc in documents.items():
                    # 分块处理文档内容
                    doc_chunks = self._chunk_document(doc_id, doc['title'], doc['content'])
                    chunks.extend(doc_chunks)
                    # 为每个分块存储原始ID
                    for i in range(len(doc_chunks)):
                        chunk_id = f"{doc_id}_chunk_{i}"
                        doc_ids.append(chunk_id)
                        self.document_map[chunk_id] = {
                            'original_id': doc_id,
                            'title': doc['title'],
                            'content': doc_chunks[i],
                            'metadata': doc.get('metadata', {})
                        }
                
                # 如果有文档，创建向量嵌入
                if chunks and self.model:
                    embeddings = self._create_embeddings(chunks)
                    if len(embeddings) > 0:
                        self.index.add(embeddings)
                        logger.info(f"已为{len(chunks)}个文档块创建索引")
            
            logger.info("FlashRAG索引初始化完成")
        except Exception as e:
            logger.exception(f"初始化FlashRAG索引时出错: {str(e)}")
            self.index = None
            raise RuntimeError(f"初始化FlashRAG索引失败，服务无法正常工作: {str(e)}")
    
    def _create_embeddings(self, texts):
        """为文本列表创建向量嵌入"""
        if not self.model or not texts:
            raise ValueError("向量模型未初始化或文本列表为空")
        
        try:
            embeddings = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
            return np.array(embeddings).astype(np.float32)
        except Exception as e:
            logger.exception(f"创建向量嵌入时出错: {str(e)}")
            raise RuntimeError(f"创建向量嵌入失败: {str(e)}")
    
    def _chunk_document(self, doc_id, title, content, chunk_size=512, overlap=50):
        """将文档内容分成更小的块"""
        if not content:
            return [title]
        
        # 合并标题和内容
        full_text = f"{title}\n\n{content}"
        
        # 如果内容较短，直接返回
        if len(full_text) <= chunk_size:
            return [full_text]
        
        # 按段落分割
        paragraphs = full_text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # 如果段落本身超过chunk_size，进一步分割
            if para_size > chunk_size:
                # 按句子分割
                sentences = para.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
                
                for sentence in sentences:
                    sentence_size = len(sentence)
                    
                    if current_size + sentence_size <= chunk_size:
                        current_chunk.append(sentence)
                        current_size += sentence_size
                    else:
                        # 保存当前块并创建新块
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                        
                        # 如果一个句子太长，可能需要进一步分割
                        if sentence_size > chunk_size:
                            # 将长句子分成较小的部分
                            for i in range(0, sentence_size, chunk_size - overlap):
                                part = sentence[i:min(i + chunk_size, sentence_size)]
                                chunks.append(part)
                        else:
                            current_chunk = [sentence]
                            current_size = sentence_size
            else:
                # 检查添加整个段落是否会超出块大小
                if current_size + para_size <= chunk_size:
                    current_chunk.append(para)
                    current_size += para_size
                else:
                    # 保存当前块并创建新块
                    if current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [para]
                    current_size = para_size
        
        # 添加最后一个块
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def search(self, query, top_k=5):
        """搜索与查询最相关的文档"""
        if not query or not self.index:
            raise ValueError("查询为空或索引未初始化")
        
        # 检查缓存
        cache_key = self._generate_cache_key(query, top_k)
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.info(f"从缓存中检索结果: {query}")
            return cached_result
        
        try:
            # 生成查询的向量表示
            if not self.model:
                raise RuntimeError("向量模型未初始化，无法执行搜索")
            
            query_vector = self.model.encode([query], convert_to_tensor=False, show_progress_bar=False)
            query_vector = np.array(query_vector).astype(np.float32)
            
            # 搜索最近的向量
            distances, indices = self.index.search(query_vector, top_k)
            
            # 获取搜索结果
            results = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and idx < len(self.document_map):  # 确保索引有效
                    chunk_id = list(self.document_map.keys())[idx]
                    doc = self.document_map[chunk_id]
                    
                    # 计算相似度分数（从L2距离转换为相似度）
                    max_distance = 100  # 假设的最大距离值
                    similarity = max(0, 1 - (distances[0][i] / max_distance))
                    
                    result = {
                        'id': doc['original_id'],
                        'chunk_id': chunk_id,
                        'title': doc['title'],
                        'content': doc['content'],
                        'similarity': float(similarity),
                        'metadata': doc.get('metadata', {})
                    }
                    results.append(result)
            
            # 使用相似度进行排序
            results = sorted(results, key=lambda x: x['similarity'], reverse=True)
            
            # 添加到缓存
            self._add_to_cache(cache_key, results)
            
            return results
        except Exception as e:
            logger.exception(f"FlashRAG搜索时出错: {str(e)}")
            raise RuntimeError(f"搜索执行失败: {str(e)}")
    
    def _generate_cache_key(self, query, top_k):
        """生成缓存键"""
        # 确保query是字符串类型
        if isinstance(query, dict):
            # 如果是字典，转换为字符串
            key_str = f"{str(query)}:{top_k}"
        else:
            key_str = f"{query.lower().strip()}:{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _add_to_cache(self, key, value):
        """添加到缓存"""
        # 如果缓存已满，移除最早的项
        if len(self.cache) >= self.cache_size:
            # 简单实现：直接清除一半的缓存
            keys = list(self.cache.keys())
            for old_key in keys[:len(keys)//2]:
                del self.cache[old_key]
        
        # 添加新项到缓存
        self.cache[key] = value
    
    def generate_answer(self, query, context, provider="deepseek"):
        """
        生成问题的答案
        使用RAG系统让语言模型基于上下文生成答案
        
        Args:
            query: 用户问题
            context: 检索到的文档内容
            provider: AI服务提供商
            
        Returns:
            包含答案和来源的结果
        """
        import requests
        import os
        import json
        import time
        
        # 整理上下文
        formatted_context = ""
        sources = []
        
        for i, doc in enumerate(context):
            formatted_context += f"文档{i+1}: {doc['content']}\n\n"
            sources.append({
                "title": doc['title'],
                "id": doc['id']
            })
        
        # 构建系统提示
        system_prompt = f"""你是一个智能问答助手。请基于以下文档内容回答用户的问题。
如果文档中没有相关信息，请诚实地说不知道，不要编造答案。
回答时引用文档编号，如"根据文档1，..."。

{formatted_context}"""
        
        # 获取API设置
        DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
        DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        OPENAI_API_URL = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
        OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/chat")
        
        try:
            answer = ""
            
            if provider == "deepseek" and DEEPSEEK_API_KEY:
                # 调用DeepSeek API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                }
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.7
                }
                response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"]
                else:
                    error_msg = f"DeepSeek API调用失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "message": error_msg
                    }
            
            elif provider == "openai" and OPENAI_API_KEY:
                # 调用OpenAI API
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.7
                }
                response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"]
                else:
                    error_msg = f"OpenAI API调用失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "message": error_msg
                    }
            
            elif provider == "ollama":
                # 调用Ollama API
                payload = {
                    "model": "llama2",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ]
                }
                response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["message"]["content"]
                else:
                    error_msg = f"Ollama API调用失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "message": error_msg
                    }
            
            # 如果没有获取到答案，返回错误信息
            if not answer:
                provider_error = {
                    "deepseek": "DeepSeek API密钥未设置或调用失败",
                    "openai": "OpenAI API密钥未设置或调用失败",
                    "ollama": "Ollama服务未启动或调用失败"
                }.get(provider, f"未知的提供商: {provider}")
                
                error_msg = f"无法获取答案: {provider_error}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg
                }
            
            return {
                "success": True,
                "data": {
                    "answer": answer,
                    "sources": sources,
                    "model": f"FlashRAG+{provider}"
                }
            }
        
        except Exception as e:
            error_msg = f"生成答案时出错: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
    
    def rag_query(self, query, provider="deepseek", top_k=3):
        """
        执行完整的FlashRAG查询
        包括检索和生成两个阶段
        
        Args:
            query: 用户问题
            provider: AI服务提供商
            top_k: 检索的文档数量
            
        Returns:
            包含答案和来源的结果
        """
        try:
            # 1. 检索相关文档
            relevant_docs = self.search(query, top_k=top_k)
            
            # 2. 基于检索到的文档生成答案
            if relevant_docs:
                return self.generate_answer(query, relevant_docs, provider)
            else:
                # 如果没有检索到相关文档，直接使用DeepSeek进行回答
                import requests
                import os
                import json
                
                # 获取DeepSeek API设置
                DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
                DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
                
                if not DEEPSEEK_API_KEY:
                    return {
                        "success": False,
                        "message": "在知识库中没有找到相关信息，且DeepSeek API密钥未设置，无法继续回答。"
                    }
                
                try:
                    # 构建系统提示
                    system_prompt = "你是一个智能问答助手。请回答用户的问题。如果你不确定答案，请诚实地说不知道。"
                    
                    # 调用DeepSeek API
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                    }
                    payload = {
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query}
                        ],
                        "temperature": 0.7
                    }
                    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        answer = data["choices"][0]["message"]["content"]
                        
                        return {
                            "success": True,
                            "data": {
                                "answer": answer,
                                "sources": [],
                                "model": "DeepSeek AI"
                            }
                        }
                    else:
                        error_msg = f"DeepSeek API调用失败: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "message": error_msg
                        }
                except Exception as e:
                    error_msg = f"调用DeepSeek时出错: {str(e)}"
                    logger.exception(error_msg)
                    return {
                        "success": False,
                        "message": error_msg
                    }
        except Exception as e:
            error_msg = f"执行FlashRAG查询时出错: {str(e)}"
            logger.exception(error_msg)
            return {
                "success": False,
                "message": error_msg
            }

# 创建FlashRAG服务实例
flashrag_service = FlashRAGService() 