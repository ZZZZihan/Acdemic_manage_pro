import logging

# 配置日志
logger = logging.getLogger(__name__)

class DummyVectorKnowledgeBase:
    """
    空的向量知识库类，用于替代原来的向量知识库
    """
    
    def __init__(self, knowledge_file=None):
        logger.info("已禁用向量知识库，FlashRAG将使用独立向量索引")
    
    def add_document(self, document):
        # 为了兼容性提供一个空的方法
        return True
    
    def search_documents(self, query, top_k=3):
        # 为了兼容性提供一个空的方法
        return []

# 创建默认的向量知识库实例
vector_knowledge_base = DummyVectorKnowledgeBase() 