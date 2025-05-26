"""
启动优化工具
用于控制应用启动时的性能和日志输出
"""

import os
import logging

# 配置日志
logger = logging.getLogger(__name__)

class StartupOptimizer:
    """启动优化器"""
    
    def __init__(self):
        # 从环境变量读取配置
        self.disable_vector_model = os.environ.get('DISABLE_VECTOR_MODEL', 'false').lower() == 'true'
        self.enable_vector_cache = os.environ.get('ENABLE_VECTOR_CACHE', 'true').lower() == 'true'
        self.vector_batch_size = int(os.environ.get('VECTOR_BATCH_SIZE', '32'))
        self.verbose_startup = os.environ.get('VERBOSE_STARTUP', 'false').lower() == 'true'
        
        # 设置tokenizers并行处理
        tokenizers_parallelism = os.environ.get('TOKENIZERS_PARALLELISM', 'false')
        os.environ['TOKENIZERS_PARALLELISM'] = tokenizers_parallelism
        
        # 如果不是详细模式，减少日志输出
        if not self.verbose_startup:
            self._reduce_logging()
    
    def _reduce_logging(self):
        """减少启动时的日志输出"""
        # 设置特定库的日志级别
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)
        logging.getLogger('datasets').setLevel(logging.WARNING)
        logging.getLogger('huggingface_hub').setLevel(logging.WARNING)
        
        # 禁用进度条
        os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = 'true'
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = 'true'
    
    def should_disable_vector_model(self) -> bool:
        """是否应该禁用向量模型"""
        return self.disable_vector_model
    
    def should_enable_vector_cache(self) -> bool:
        """是否应该启用向量缓存"""
        return self.enable_vector_cache
    
    def get_vector_batch_size(self) -> int:
        """获取向量批次大小"""
        return self.vector_batch_size
    
    def is_verbose_startup(self) -> bool:
        """是否启用详细启动日志"""
        return self.verbose_startup
    
    def print_startup_info(self):
        """打印启动优化信息"""
        if self.verbose_startup:
            logger.info("=== 启动优化配置 ===")
            logger.info(f"禁用向量模型: {self.disable_vector_model}")
            logger.info(f"启用向量缓存: {self.enable_vector_cache}")
            logger.info(f"向量批次大小: {self.vector_batch_size}")
            logger.info(f"详细启动日志: {self.verbose_startup}")
            logger.info("==================")
        else:
            logger.info("启动优化已启用，使用详细模式请设置 VERBOSE_STARTUP=true")

# 创建全局实例
startup_optimizer = StartupOptimizer() 