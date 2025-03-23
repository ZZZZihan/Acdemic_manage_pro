import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeBase:
    """知识库管理类，用于存储和检索技术总结内容"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化知识库
        
        Args:
            storage_path: 知识库存储路径，默认为app目录下的knowledge_base.json
        """
        self.storage_path = storage_path or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'knowledge_base.json')
        self.documents = {}
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """从文件加载知识库"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                logger.info(f"已从{self.storage_path}加载知识库，共{len(self.documents)}篇文档")
            else:
                logger.info(f"知识库文件{self.storage_path}不存在，将创建新的知识库")
                self.documents = {}
                self._save_knowledge_base()
        except Exception as e:
            logger.error(f"加载知识库时出错: {str(e)}")
            self.documents = {}
    
    def _save_knowledge_base(self):
        """保存知识库到文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存知识库到{self.storage_path}，共{len(self.documents)}篇文档")
        except Exception as e:
            logger.error(f"保存知识库时出错: {str(e)}")
    
    def add_document(self, doc_id: str, title: str, content: str, metadata: Dict = None):
        """
        添加文档到知识库
        
        Args:
            doc_id: 文档ID
            title: 文档标题
            content: 文档内容
            metadata: 文档元数据
        """
        try:
            self.documents[doc_id] = {
                'title': title,
                'content': content,
                'metadata': metadata or {},
                'updated_at': datetime.now().isoformat()
            }
            self._save_knowledge_base()
            logger.info(f"已添加文档到知识库: {title} (ID: {doc_id})")
            return True
        except Exception as e:
            logger.error(f"添加文档到知识库时出错: {str(e)}")
            return False
    
    def remove_document(self, doc_id: str):
        """
        从知识库中移除文档
        
        Args:
            doc_id: 文档ID
        """
        try:
            if doc_id in self.documents:
                title = self.documents[doc_id]['title']
                del self.documents[doc_id]
                self._save_knowledge_base()
                logger.info(f"已从知识库中移除文档: {title} (ID: {doc_id})")
                return True
            else:
                logger.warning(f"文档ID {doc_id} 不存在于知识库中")
                return False
        except Exception as e:
            logger.error(f"从知识库中移除文档时出错: {str(e)}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        获取知识库中的文档
        
        Args:
            doc_id: 文档ID
            
        Returns:
            文档内容，如果不存在则返回None
        """
        return self.documents.get(doc_id)
    
    def search_documents(self, query: str) -> List[Dict]:
        """
        搜索知识库中的文档
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的文档列表
        """
        results = []
        query_lower = query.lower()
        
        for doc_id, doc in self.documents.items():
            # 在标题和内容中搜索关键词
            if query_lower in doc['title'].lower() or query_lower in doc['content'].lower():
                # 添加文档ID
                doc_copy = doc.copy()
                doc_copy['id'] = doc_id
                results.append(doc_copy)
        
        return results
    
    def get_all_documents(self) -> Dict[str, Dict]:
        """
        获取知识库中的所有文档
        
        Returns:
            所有文档的字典
        """
        return self.documents

# 创建知识库实例
knowledge_base = KnowledgeBase() 