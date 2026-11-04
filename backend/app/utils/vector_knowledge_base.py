import logging
import json
import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
from .startup_optimizer import startup_optimizer

# 配置日志
logger = logging.getLogger(__name__)

class VectorKnowledgeBase:
    """
    向量知识库类
    使用向量嵌入来检索相关文档
    """
    
    def __init__(self, knowledge_file: str = None, cache_dir: str = None):
        """
        初始化向量知识库
        
        Args:
            knowledge_file: 知识库文件路径，默认为None则使用内存存储
            cache_dir: 缓存目录，用于存储预计算的向量
        """
        # 设置缓存目录
        self.cache_dir = cache_dir or os.path.join(os.path.dirname(__file__), '..', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 延迟初始化模型
        self.model = None
        self.use_mock = False
        self._model_loaded = False
        
        # 文档和向量存储
        self.documents = []  # 存储文档
        self.embeddings = []  # 存储文档向量
        self._embeddings_loaded = False
        
        # 如果提供了知识库文件，则加载文档（但不立即生成向量）
        if knowledge_file and os.path.exists(knowledge_file):
            self._load_documents_only(knowledge_file)
    
    def _load_model(self) -> None:
        """延迟加载向量模型"""
        if self._model_loaded:
            return
        
        # 检查是否禁用向量模型
        if startup_optimizer.should_disable_vector_model():
            logger.info("向量模型已被禁用，使用模拟模式")
            self.model = None
            self.use_mock = True
            self._model_loaded = True
            return
            
        try:
            if not startup_optimizer.is_verbose_startup():
                logger.info("正在加载句向量模型...")
            else:
                logger.info("正在加载句向量模型: paraphrase-multilingual-MiniLM-L12-v2")
                
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.use_mock = False
            self._model_loaded = True
            logger.info("成功加载句向量模型")
        except Exception as e:
            logger.warning(f"加载句向量模型失败，将使用模拟模式: {str(e)}")
            self.model = None
            self.use_mock = True
            self._model_loaded = True
    
    def _load_documents_only(self, knowledge_file: str) -> None:
        """只加载文档，不生成向量（延迟到需要时再生成）"""
        try:
            with open(knowledge_file, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)
            
            logger.info(f"已从{knowledge_file}加载知识库，共{len(self.documents)}篇文档")
        except Exception as e:
            logger.exception(f"加载知识库失败: {str(e)}")
            self.documents = []
    
    def load_knowledge(self, knowledge_file: str) -> None:
        """
        从文件加载知识库
        
        Args:
            knowledge_file: 知识库文件路径
        """
        self._load_documents_only(knowledge_file)
        
        # 尝试从缓存加载向量
        if self.documents:
            self._load_embeddings_from_cache(knowledge_file)
    
    def _get_cache_path(self, knowledge_file: str) -> str:
        """获取缓存文件路径"""
        # 基于知识库文件的修改时间和内容生成缓存文件名
        import hashlib
        
        file_stat = os.stat(knowledge_file)
        cache_key = f"{knowledge_file}_{file_stat.st_mtime}_{len(self.documents)}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        
        return os.path.join(self.cache_dir, f"embeddings_{cache_hash}.pkl")
    
    def _load_embeddings_from_cache(self, knowledge_file: str) -> bool:
        """从缓存加载向量嵌入"""
        if not startup_optimizer.should_enable_vector_cache():
            return False
            
        cache_path = self._get_cache_path(knowledge_file)
        
        try:
            if os.path.exists(cache_path):
                if startup_optimizer.is_verbose_startup():
                    logger.info(f"正在从缓存加载向量嵌入: {cache_path}")
                else:
                    logger.info("正在从缓存加载向量嵌入...")
                    
                with open(cache_path, 'rb') as f:
                    self.embeddings = pickle.load(f)
                self._embeddings_loaded = True
                logger.info(f"✅ 成功从缓存加载 {len(self.embeddings)} 个向量嵌入")
                return True
        except Exception as e:
            logger.warning(f"从缓存加载向量嵌入失败: {str(e)}")
        
        return False
    
    def _save_embeddings_to_cache(self, knowledge_file: str) -> None:
        """保存向量嵌入到缓存"""
        if not startup_optimizer.should_enable_vector_cache():
            return
            
        if not self.embeddings or len(self.embeddings) == 0:
            return
            
        cache_path = self._get_cache_path(knowledge_file)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(self.embeddings, f)
            if startup_optimizer.is_verbose_startup():
                logger.info(f"已保存向量嵌入到缓存: {cache_path}")
            else:
                logger.info(f"✅ 已保存 {len(self.embeddings)} 个向量嵌入到缓存")
        except Exception as e:
            logger.warning(f"保存向量嵌入到缓存失败: {str(e)}")
    
    def _ensure_embeddings_loaded(self, knowledge_file: str = None) -> None:
        """确保向量嵌入已加载"""
        if self._embeddings_loaded or self.use_mock or not self.documents:
            return
        
        # 首先尝试加载模型
        self._load_model()
        
        if self.use_mock:
            return
        
        # 如果有缓存，尝试加载
        if knowledge_file and self._load_embeddings_from_cache(knowledge_file):
            return
        
        # 否则生成新的向量嵌入
        if startup_optimizer.is_verbose_startup():
            logger.info("正在生成向量嵌入...")
        else:
            logger.info("🔄 正在生成向量嵌入，请稍候...")
        self._generate_embeddings()
        
        # 保存到缓存
        if knowledge_file:
            self._save_embeddings_to_cache(knowledge_file)
    
    def _generate_embeddings(self) -> None:
        """为所有文档生成向量嵌入"""
        if self.use_mock or not self.documents:
            return
        
        try:
            # 提取文档内容
            texts = [f"{doc['title']}. {doc['content']}" for doc in self.documents]
            
            # 批量生成向量嵌入，显示进度
            batch_size = startup_optimizer.get_vector_batch_size()
            all_embeddings = []
            
            if startup_optimizer.is_verbose_startup():
                logger.info(f"使用批次大小: {batch_size}")
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(
                    batch_texts, 
                    convert_to_numpy=True,
                    show_progress_bar=startup_optimizer.is_verbose_startup()  # 根据配置显示进度条
                )
                all_embeddings.append(batch_embeddings)
            
            # 合并所有批次的嵌入
            if all_embeddings:
                self.embeddings = np.vstack(all_embeddings)
                self._embeddings_loaded = True
                if startup_optimizer.is_verbose_startup():
                    logger.info(f"已为{len(self.documents)}篇文档生成向量嵌入")
                else:
                    logger.info(f"✅ 已为 {len(self.documents)} 篇文档生成向量嵌入")
            
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
            
            # 如果已经加载了向量，为新文档生成向量
            if self._embeddings_loaded and not self.use_mock:
                self._load_model()  # 确保模型已加载
                
                if not self.use_mock:
                    text = f"{document['title']}. {document['content']}"
                    embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
                    
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
        # 确保向量嵌入已加载
        self._ensure_embeddings_loaded()
        
        if self.use_mock:
            return self._mock_search(query, top_k)
        
        if not self.documents or len(self.embeddings) == 0:
            logger.warning("知识库为空，无法搜索")
            return []
        
        try:
            # 生成查询向量
            query_embedding = self.model.encode(query, convert_to_numpy=True, show_progress_bar=False)
            
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