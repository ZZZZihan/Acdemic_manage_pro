from flask import Blueprint, request, jsonify
from app.utils.ollama_chat import OllamaChat
import logging

# 创建蓝图
ollama_bp = Blueprint('ollama', __name__)

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建Ollama客户端
ollama_client = OllamaChat()

@ollama_bp.route('/chat', methods=['POST'])
def chat():
    """
    与Ollama模型聊天的API端点
    
    Returns:
        JSON响应，包含模型的回答
    """
    try:
        # 从请求中获取数据
        data = request.get_json()
        
        # 验证必需参数
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必需的参数: query'
            }), 400
        
        query = data.get('query', '')
        
        # 调用Ollama客户端进行聊天
        result = ollama_client.chat(query)
        
        # 返回结果
        return jsonify(result)
        
    except Exception as e:
        logger.exception(f"Ollama聊天API出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        }), 500 