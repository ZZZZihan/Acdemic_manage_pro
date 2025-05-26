from flask import request, jsonify, Blueprint
from app.utils.flashrag_service import flashrag_service
import logging

rag_bp = Blueprint('rag', __name__)
logger = logging.getLogger(__name__)

@rag_bp.route('/chat', methods=['POST'])
def rag_chat():
    """
    RAG智能问答接口
    ---
    请求体:
    {
        "query": "问题内容",
        "provider": "llm提供商(可选，默认为deepseek)"
    }
    
    响应:
    {
        "success": 布尔值,
        "data": {
            "answer": "回答内容",
            "sources": [{"title": "来源标题", "id": "来源ID"}, ...],
            "model": "模型名称"
        }
    }
    
    错误响应:
    {
        "success": false,
        "message": "错误信息"
    }
    """
    data = request.get_json()
    
    # 记录请求
    logger.info(f"RAG请求: {data}")
    
    # 验证必要字段
    if not data or 'query' not in data:
        return jsonify({
            "success": False,
            "message": "缺少必要参数"
        }), 400
    
    query = data.get('query')
    provider = data.get('provider', 'deepseek')
    
    try:
        # 直接使用FlashRAG服务
        result = flashrag_service.rag_query(query, provider)
        
        return jsonify(result)
    except Exception as e:
        logger.exception(f"处理RAG请求时出错: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"处理请求时出错: {str(e)}"
        }), 500

@rag_bp.route('/init_flashrag', methods=['POST'])
def init_flashrag():
    """
    初始化FlashRAG索引
    ---
    响应:
    {
        "success": 布尔值,
        "message": "结果信息"
    }
    """
    try:
        # 重新初始化FlashRAG服务
        flashrag_service._init_index()
        
        return jsonify({
            "success": True,
            "message": "FlashRAG索引初始化成功"
        })
    except Exception as e:
        logger.exception(f"初始化FlashRAG索引时出错: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"初始化FlashRAG索引时出错: {str(e)}"
        }), 500