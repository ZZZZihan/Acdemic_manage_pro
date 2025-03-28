import logging
import json
import os
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

# 配置日志
logger = logging.getLogger(__name__)

class VectorKnowledgeBase:
    """
    向量知识库类
    使用向量嵌入来检索相关文档
    """
    
    def __init__(self, knowledge_file: str = None):
        """
        初始化向量知识库
        
        Args:
            knowledge_file: 知识库文件路径，默认为None则使用内存存储
        """
        # 初始化嵌入模型
        try:
            # 尝试加载嵌入模型，如果失败则使用模拟模式
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.use_mock = False
            logger.info("成功加载句向量模型")
        except Exception as e:
            logger.warning(f"加载句向量模型失败，将使用模拟模式: {str(e)}")
            self.model = None
            self.use_mock = True
        
        # 文档和向量存储
        self.documents = []  # 存储文档
        self.embeddings = []  # 存储文档向量
        
        # 如果提供了知识库文件，则加载
        if knowledge_file and os.path.exists(knowledge_file):
            self.load_knowledge(knowledge_file)
    
    def load_knowledge(self, knowledge_file: str) -> None:
        """
        从文件加载知识库
        
        Args:
            knowledge_file: 知识库文件路径
        """
        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            logger.info(f"已从{knowledge_file}加载知识库，共{len(self.documents)}篇文档")
            
            # 为所有文档生成向量嵌入
            if not self.use_mock and self.documents:
                self._generate_embeddings()
        except Exception as e:
            logger.exception(f"加载知识库失败: {str(e)}")
            self.documents = []
            self.embeddings = []
    
    def _generate_embeddings(self) -> None:
        """为所有文档生成向量嵌入"""
        if self.use_mock or not self.documents:
            return
        
        try:
            # 提取文档内容
            texts = [f"{doc['title']}. {doc['content']}" for doc in self.documents]
            
            # 生成向量嵌入
            self.embeddings = self.model.encode(texts, convert_to_numpy=True)
            
            logger.info(f"已为{len(self.documents)}篇文档生成向量嵌入")
        except Exception as e:
            logger.exception(f"生成向量嵌入失败: {str(e)}")
            self.embeddings = []
    
    def add_document(self, document: Dict[str, Any]) -> bool:
        """
        添加文档到知识库
        
        Args:
            document: 包含title和content的文档字典
            
        Returns:
            是否添加成功
        """
        try:
            # 确保文档格式正确
            if 'title' not in document or 'content' not in document:
                logger.error("文档格式错误，必须包含title和content字段")
                return False
            
            # 为文档添加ID
            if 'id' not in document:
                document['id'] = f"doc{len(self.documents) + 1}"
            
            # 添加文档
            self.documents.append(document)
            
            # 生成向量嵌入
            if not self.use_mock:
                text = f"{document['title']}. {document['content']}"
                embedding = self.model.encode(text, convert_to_numpy=True)
                
                if len(self.embeddings) == 0:
                    self.embeddings = np.array([embedding])
                else:
                    self.embeddings = np.vstack([self.embeddings, embedding])
            
            return True
        except Exception as e:
            logger.exception(f"添加文档失败: {str(e)}")
            return False
    
    def search_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索与查询相关的文档
        
        Args:
            query: 查询文本
            top_k: 返回的最相关文档数量
            
        Returns:
            相关文档列表
        """
        if self.use_mock:
            return self._mock_search(query, top_k)
        
        if not self.documents or len(self.embeddings) == 0:
            logger.warning("知识库为空，无法搜索")
            return []
        
        try:
            # 生成查询向量
            query_embedding = self.model.encode(query, convert_to_numpy=True)
            
            # 计算相似度
            similarities = np.dot(self.embeddings, query_embedding) / (
                np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            # 获取最相关的文档索引
            top_indices = np.argsort(-similarities)[:top_k]
            
            # 返回最相关的文档
            results = []
            for i in top_indices:
                if similarities[i] > 0.3:  # 设置相似度阈值
                    doc = self.documents[i].copy()
                    doc['similarity'] = float(similarities[i])
                    results.append(doc)
            
            return results
        except Exception as e:
            logger.exception(f"搜索文档失败: {str(e)}")
            return self._mock_search(query, top_k)  # 失败时回退到模拟搜索
    
    def _mock_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        模拟搜索功能（当向量搜索不可用时）
        
        Args:
            query: 查询文本
            top_k: 返回的文档数量
            
        Returns:
            模拟的搜索结果
        """
        if not self.documents:
            return []
        
        # 简单的关键词匹配
        results = []
        query_lower = query.lower()
        
        for doc in self.documents:
            title_lower = doc['title'].lower()
            content_lower = doc['content'].lower()
            
            # 检查标题和内容中是否包含查询关键词
            if query_lower in title_lower or query_lower in content_lower:
                # 计算一个模拟的相似度分数
                # 标题匹配权重更高
                score = 0.0
                if query_lower in title_lower:
                    score += 0.8
                if query_lower in content_lower:
                    score += 0.5
                
                doc_copy = doc.copy()
                doc_copy['similarity'] = min(score, 0.99)  # 限制最大分数
                results.append(doc_copy)
        
        # 如果关键词匹配找不到结果，返回随机文档
        if not results and self.documents:
            # 选择一些随机文档
            import random
            random_docs = random.sample(
                self.documents, 
                min(top_k, len(self.documents))
            )
            for doc in random_docs:
                doc_copy = doc.copy()
                doc_copy['similarity'] = random.uniform(0.3, 0.5)  # 较低的相似度
                results.append(doc_copy)
        
        # 按相似度排序并限制返回数量
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]


# 创建默认的向量知识库实例
vector_knowledge_base = VectorKnowledgeBase()