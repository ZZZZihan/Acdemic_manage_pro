from flask import request, jsonify
from app.api.v1 import api
from app.utils.rag_service import rag_service
import logging

logger = logging.getLogger(__name__)

@api.route("/rag/chat", methods=["POST"])
def rag_chat():
    """
    RAG聊天API端点
    使用检索增强生成技术回答问题
    
    请求格式：
    {
        "query": "问题文本",
        "provider": "deepseek" // 可选，默认为deepseek
    }
    
    响应格式：
    {
        "success": true,
        "data": {
            "answer": "回答内容",
            "sources": [{"title": "来源标题", "id": "文档ID"}],
            "model": "RAG+提供商名称"
        }
    }
    """
    try:
        # 获取请求数据
        data = request.get_json() or {}
        
        # 检查必填字段
        if "query" not in data:
            return jsonify({
                "success": False,
                "message": "问题是必填项"
            }), 400
            
        # 获取AI提供商（可选）
        provider = data.get("provider", "deepseek")
        
        # 记录请求信息
        logger.info(f"RAG聊天请求: 提供商={provider}, 查询={data['query'][:30]}...")
        
        # 调用RAG服务回答问题
        result = rag_service.answer_question(data["query"], provider)
        
        return jsonify(result)
            
    except Exception as e:
        logger.exception(f"处理RAG聊天请求时出错: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"处理请求时出错: {str(e)}"
        }), 500