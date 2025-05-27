from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api
from app.models import TechSummary, User, db
from app.api.v1.errors import bad_request, not_found, unauthorized
import logging
from datetime import datetime
from app.utils.crawler import crawl_url
from app.utils.llm_api import llm_service
from app.utils.chat_with_doc import chat_with_document, chat_with_knowledge_base
from app.utils.knowledge_base import knowledge_base

@api.route('/tech_summaries', methods=['GET'])
def get_tech_summaries():
    """获取技术总结列表"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 是否只返回当前用户的技术总结
    only_mine = request.args.get('only_mine', 'false', type=str).lower() == 'true'
    
    # 获取筛选参数
    summary_type = request.args.get('type', '')
    keyword = request.args.get('keyword', '')
    tags = request.args.get('tags', '')
    
    # 构建查询
    query = TechSummary.query
    
    # 应用筛选条件
    if summary_type:
        query = query.filter(TechSummary.summary_type == summary_type)
    
    if keyword:
        # 在标题和内容中搜索关键词
        query = query.filter(
            db.or_(
                TechSummary.title.ilike(f'%{keyword}%'),
                TechSummary.content.ilike(f'%{keyword}%')
            )
        )
    
    if tags:
        # 在标签中搜索
        for tag in tags.split(','):
            query = query.filter(TechSummary.tags.ilike(f'%{tag.strip()}%'))
    
    # 如果需要只返回当前用户的技术总结，并且用户已登录
    if only_mine and request.headers.get('Authorization'):
        try:
            # 从JWT中获取用户ID
            current_user_id = get_jwt_identity()
            if current_user_id:
                query = query.filter_by(user_id=current_user_id)
        except Exception as e:
            logging.error(f"获取用户ID时出错: {e}")
    
    # 执行分页查询
    pagination = query.order_by(TechSummary.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    summaries = pagination.items
    total = pagination.total
    
    return jsonify({
        'items': [summary.to_dict() for summary in summaries],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

@api.route('/tech_summaries/<int:id>', methods=['GET'])
def get_tech_summary(id):
    """获取指定ID的技术总结"""
    summary = TechSummary.query.get(id)
    if not summary:
        return not_found('技术总结不存在')
    
    return jsonify(summary.to_dict())

@api.route('/tech_summaries', methods=['POST'])
@jwt_required()
def create_tech_summary():
    """创建新技术总结"""
    current_user_id = get_jwt_identity()
    
    # 获取请求数据
    data = request.get_json() or {}
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    # 检查必填字段
    if 'title' not in data:
        return bad_request('技术总结标题是必填项')
    
    if 'content' not in data:
        return bad_request('技术总结内容是必填项')
    
    # 创建新的技术总结记录
    summary = TechSummary(
        user_id=current_user_id,
        title=str(data.get('title', '')),
        content=str(data.get('content', '')),
        summary_type=str(data.get('summary_type', '其他')),
        tags=str(data.get('tags', '')),
        file_path=str(data.get('file_path', '')),
        original_file_name=str(data.get('original_file_name', '')),
        source_url=str(data.get('source_url', ''))
    )
    
    # 处理文件路径和原始文件名
    if 'file_path' in data:
        summary.file_path = str(data.get('file_path', ''))
    if 'original_file_name' in data:
        summary.original_file_name = str(data.get('original_file_name', ''))
    
    # 处理来源URL
    if 'source_url' in data:
        summary.source_url = str(data.get('source_url', ''))
    
    try:
        db.session.add(summary)
        db.session.commit()
        
        # 将技术总结添加到知识库
        add_tech_summary_to_knowledge_base(summary)
        
        return jsonify(summary.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"创建技术总结时发生错误: {e}")
        return jsonify({"msg": f"创建技术总结失败: {str(e)}"}), 500

@api.route('/tech_summaries/<int:id>', methods=['PUT'])
@jwt_required()
def update_tech_summary(id):
    """更新指定ID的技术总结"""
    current_user_id = get_jwt_identity()
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    summary = TechSummary.query.get(id)
    if not summary:
        return not_found('技术总结不存在')
    
    if summary.user_id != current_user_id:
        return unauthorized('无权修改此技术总结')
    
    data = request.get_json() or {}
    
    # 更新字段
    if 'title' in data:
        summary.title = str(data['title'])
    if 'content' in data:
        summary.content = str(data['content'])
    if 'summary_type' in data:
        summary.summary_type = str(data['summary_type'])
    if 'tags' in data:
        summary.tags = str(data['tags'])
    if 'file_path' in data:
        summary.file_path = str(data['file_path'])
    if 'original_file_name' in data:
        summary.original_file_name = str(data['original_file_name'])
    if 'source_url' in data:
        summary.source_url = str(data['source_url'])
    
    summary.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # 更新知识库中的技术总结
        add_tech_summary_to_knowledge_base(summary)
        
        return jsonify(summary.to_dict())
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新技术总结时发生错误: {e}")
        return jsonify({"msg": f"更新技术总结失败: {str(e)}"}), 500

@api.route('/tech_summaries/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_tech_summary(id):
    """删除指定ID的技术总结"""
    current_user_id = get_jwt_identity()
    logging.info(f"删除技术总结请求 - ID: {id}, 当前用户ID: {current_user_id}, 类型: {type(current_user_id)}")
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
            logging.info(f"用户ID转换为整数: {current_user_id}")
        except ValueError:
            logging.error(f"无效的用户ID: {current_user_id}")
            return jsonify({"msg": "无效的用户ID"}), 400
    
    summary = TechSummary.query.get(id)
    if not summary:
        logging.warning(f"技术总结不存在 - ID: {id}")
        return not_found('技术总结不存在')
    
    # 获取当前用户信息
    current_user = User.query.get(current_user_id)
    if not current_user:
        logging.error(f"用户不存在 - ID: {current_user_id}")
        return unauthorized('用户不存在')
    
    logging.info(f"技术总结信息 - ID: {id}, 标题: {summary.title}, 创建者ID: {summary.user_id}, 类型: {type(summary.user_id)}")
    logging.info(f"当前用户信息 - ID: {current_user_id}, 用户名: {current_user.username}, 是否管理员: {current_user.is_administrator()}")
    
    # 权限检查：创建者或管理员可以删除
    is_owner = summary.user_id == current_user_id
    is_admin = current_user.is_administrator()
    
    logging.info(f"权限检查 - 是否创建者: {is_owner}, 是否管理员: {is_admin}")
    
    if not (is_owner or is_admin):
        logging.warning(f"权限不足 - 用户 {current_user_id} ({current_user.username}) 尝试删除用户 {summary.user_id} 创建的技术总结 {id}")
        return unauthorized('无权删除此技术总结，只有创建者或管理员可以删除')
    
    # 记录删除操作
    if is_admin and not is_owner:
        logging.info(f"管理员删除操作 - 管理员 {current_user.username} (ID: {current_user_id}) 删除了用户 {summary.user_id} 创建的技术总结 '{summary.title}' (ID: {id})")
    
    # 从知识库中移除技术总结
    try:
        knowledge_base.remove_document(str(id))
        logging.info(f"已从知识库中移除技术总结 '{summary.title}' (ID: {id})")
    except Exception as e:
        logging.error(f"从知识库中移除技术总结时出错: {str(e)}")
    
    db.session.delete(summary)
    db.session.commit()
    logging.info(f"技术总结删除成功 - ID: {id}")
    
    return jsonify({'message': '技术总结已删除'})

@api.route('/tech_summaries/crawl', methods=['POST'])
@jwt_required()
def crawl_and_summarize():
    """爬取URL内容并使用大语言模型进行总结"""
    data = request.get_json() or {}
    
    # 检查必填字段
    if 'url' not in data:
        return bad_request('URL是必填项')
    
    url = data.get('url', '')
    provider = data.get('provider', 'deepseek')  # 默认使用DeepSeek
    custom_prompt = data.get('custom_prompt', None)  # 可选的自定义提示词
    
    # 爬取URL内容
    crawl_result = crawl_url(url)
    
    if not crawl_result['success']:
        return jsonify({
            'success': False,
            'message': crawl_result['message']
        }), 400
    
    # 提取爬取的内容
    crawled_data = crawl_result['data']
    content = crawled_data['content']
    original_title = crawled_data['title']
    
    # 使用大语言模型进行总结
    summary_result = llm_service.summarize_content(
        content=content,
        url=url,
        provider=provider,
        prompt=custom_prompt
    )
    
    if not summary_result['success']:
        return jsonify({
            'success': False,
            'message': summary_result['message']
        }), 400
    
    # 提取总结内容
    summary_data = summary_result['data']
    summary = summary_data['summary']
    
    # 使用AI生成的标题，如果没有则使用原始标题
    ai_title = summary_data.get('title', '')
    title = ai_title if ai_title else original_title
    
    # 返回结果
    return jsonify({
        'success': True,
        'message': '爬取和总结成功',
        'data': {
            'title': title,
            'content': summary,
            'url': url,
            'original_content': content,
            'original_title': original_title,
            'provider': summary_data['provider'],
            'model': summary_data['model'],
            'tags': summary_data.get('tags', '')
        }
    }) 

@api.route('/tech_summaries/<int:id>/chat', methods=['POST'])
def chat_with_tech_summary(id):
    """基于技术总结内容进行聊天"""
    # 获取技术总结
    summary = TechSummary.query.get(id)
    if not summary:
        return not_found('技术总结不存在')
    
    # 获取请求数据
    data = request.get_json() or {}
    
    # 检查必填字段
    if 'query' not in data:
        return bad_request('问题是必填项')
    
    # 获取AI提供商
    provider = data.get('provider', 'deepseek')
    
    # 获取是否使用知识库
    use_knowledge_base = data.get('use_knowledge_base', False)
    
    try:
        if use_knowledge_base:
            # 使用知识库回答问题
            result = chat_with_knowledge_base(data['query'], str(id), provider)
        else:
            # 使用单个文档内容回答问题
            result = chat_with_document(summary.content, data['query'], provider)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'answer': result['answer'],
                    'provider': result['provider']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '处理问题时出错')
            }), 500
    except Exception as e:
        logging.exception(f"处理聊天请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        }), 500

@api.route('/knowledge_base/chat', methods=['POST'])
def chat_with_global_knowledge_base():
    """基于全局知识库进行聊天"""
    # 获取请求数据
    data = request.get_json() or {}
    
    # 检查必填字段
    if 'query' not in data:
        return bad_request('问题是必填项')
    
    # 获取AI提供商
    provider = data.get('provider', 'deepseek')
    
    try:
        # 使用知识库回答问题
        result = chat_with_knowledge_base(data['query'], None, provider)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': {
                    'answer': result['answer'],
                    'provider': result['provider']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', '处理问题时出错')
            }), 500
    except Exception as e:
        logging.exception(f"处理全局知识库聊天请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        }), 500

@api.route('/ai/chat', methods=['POST'])
def pure_ai_chat():
    """纯AI聊天，不使用知识库"""
    # 获取请求数据
    data = request.get_json() or {}
    
    # 检查必填字段
    if 'query' not in data:
        return bad_request('问题是必填项')
    
    # 获取AI提供商
    provider = data.get('provider', 'deepseek')
    
    try:
        # 直接调用AI API，不使用知识库
        from app.utils.chat_with_doc import _call_ai_api
        
        # 构建系统提示
        system_prompt = """你是一个专业的AI助手。请直接回答用户的问题，提供准确、详细、有用的信息。

请用中文回答，要准确、详细、全面。请提供完整的解释和具体的步骤，包括：
1. 详细的概念解释
2. 具体的实施步骤或方法
3. 相关的技术细节
4. 实际应用场景或示例
5. 注意事项或最佳实践

回答应该具有教学性质，帮助用户深入理解相关内容。"""
        
        # 调用AI API
        ai_answer = _call_ai_api(data['query'], system_prompt, provider)
        
        if ai_answer:
            return jsonify({
                'success': True,
                'data': {
                    'answer': ai_answer,
                    'provider': provider,
                    'mode': 'pure_ai'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{provider} API调用失败，请稍后重试'
            }), 500
            
    except Exception as e:
        logging.exception(f"处理纯AI聊天请求时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理请求时出错: {str(e)}'
        }), 500

# 添加技术总结到知识库的钩子函数
def add_tech_summary_to_knowledge_base(tech_summary):
    """将技术总结添加到知识库"""
    try:
        knowledge_base.add_document(
            doc_id=str(tech_summary.id),
            title=tech_summary.title,
            content=tech_summary.content,
            metadata={
                'summary_type': tech_summary.summary_type,
                'tags': tech_summary.tags,
                'created_at': tech_summary.created_at.isoformat() if tech_summary.created_at else None,
                'updated_at': tech_summary.updated_at.isoformat() if tech_summary.updated_at else None,
                'user_id': tech_summary.user_id,
                'source_url': tech_summary.source_url
            }
        )
        logging.info(f"已将技术总结 '{tech_summary.title}' (ID: {tech_summary.id}) 添加到知识库")
    except Exception as e:
        logging.error(f"将技术总结添加到知识库时出错: {str(e)}")

# 添加初始化知识库的API
@api.route('/knowledge_base/init', methods=['POST'])
@jwt_required()
def init_knowledge_base():
    """初始化知识库，将所有技术总结添加到知识库"""
    try:
        # 获取所有技术总结
        summaries = TechSummary.query.all()
        
        # 添加到知识库
        for summary in summaries:
            add_tech_summary_to_knowledge_base(summary)
        
        return jsonify({
            'success': True,
            'message': f'已成功将{len(summaries)}篇技术总结添加到知识库'
        })
    except Exception as e:
        logging.exception(f"初始化知识库时出错: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'初始化知识库时出错: {str(e)}'
        }), 500

# 添加调试API端点
@api.route('/tech_summaries/<int:id>/debug', methods=['GET'])
@jwt_required()
def debug_tech_summary_ownership(id):
    """调试技术总结所有权信息"""
    current_user_id = get_jwt_identity()
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    summary = TechSummary.query.get(id)
    if not summary:
        return not_found('技术总结不存在')
    
    # 获取用户信息
    user = User.query.get(current_user_id)
    creator = User.query.get(summary.user_id)
    
    # 权限检查
    is_owner = summary.user_id == current_user_id
    is_admin = user.is_administrator() if user else False
    can_delete = is_owner or is_admin
    
    debug_info = {
        'current_user': {
            'id': current_user_id,
            'type': str(type(current_user_id)),
            'username': user.username if user else 'Unknown',
            'email': user.email if user else 'Unknown',
            'is_administrator': is_admin,
            'role': user.role.name if user and user.role else 'No Role'
        },
        'summary': {
            'id': summary.id,
            'title': summary.title,
            'creator_id': summary.user_id,
            'creator_type': str(type(summary.user_id)),
            'creator_username': creator.username if creator else 'Unknown',
            'creator_email': creator.email if creator else 'Unknown'
        },
        'permission_check': {
            'is_owner': is_owner,
            'is_admin': is_admin,
            'can_delete': can_delete,
            'reason': 'Owner' if is_owner else ('Admin' if is_admin else 'No Permission'),
            'comparison': f"{summary.user_id} == {current_user_id}"
        }
    }
    
    return jsonify(debug_info)