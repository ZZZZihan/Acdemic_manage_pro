from flask import request, jsonify
from app.api.v1 import api
from app.utils.ollama_chat import OllamaChat
import logging

logger = logging.getLogger(__name__)

# 创建Ollama聊天实例
ollama_chat = OllamaChat()

@api.route('/ollama/chat', methods=['POST'])
def chat():
    """处理Ollama聊天请求"""
    try:
        # 获取请求数据
        data = request.get_json() or {}
        
        # 检查必填字段
        if 'query' not in data:
            return jsonify({
                'success': False,
                'message': '问题是必填项'
            }), 400
            
        # 获取是否使用模拟模式
        use_mock = data.get('use_mock', True)
        
        # 调用Ollama聊天
        result = ollama_chat.chat(data['query'], use_mock)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.exception(f"处理Ollama聊天请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        }), 500 