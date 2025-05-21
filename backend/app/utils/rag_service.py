import logging

# 配置日志
logger = logging.getLogger(__name__)

class DummyRAGService:
    """
    空的RAG服务类，用于替代原来的标准RAG服务
    """
    
    def __init__(self):
        logger.info("已禁用标准RAG服务，仅使用FlashRAG服务")
    
    def _generate_answer(self, *args, **kwargs):
        # 为了兼容性提供一个空的方法
        return "此功能已禁用，请使用FlashRAG服务", []

# 创建虚拟服务实例
rag_service = DummyRAGService()