from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api
from app.models import Achievement, User, db
from app.api.v1.errors import bad_request, not_found, unauthorized
import logging
import json
from datetime import datetime, date

@api.route('/achievements/latest', methods=['GET'])
def get_latest_achievements():
    """获取最新成果"""
    # 获取参数：limit表示返回条数，默认为5条
    limit = request.args.get('limit', 5, type=int)
    
    # 查询最新成果，按创建时间倒序排列
    achievements = Achievement.query.order_by(Achievement.created_at.desc()).limit(limit).all()
    
    # 构建返回结果
    result = [achievement.to_dict() for achievement in achievements]
    
    return jsonify(result)

@api.route('/achievements', methods=['GET'])
def get_achievements():
    """获取成果列表"""
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # 是否只返回当前用户的成果
    only_mine = request.args.get('only_mine', 'false', type=str).lower() == 'true'
    
    # 获取筛选参数
    achievement_type = request.args.get('type', '')
    keyword = request.args.get('keyword', '')
    
    # 构建查询
    query = Achievement.query
    
    # 应用筛选条件
    if achievement_type:
        query = query.filter(Achievement.achievement_type == achievement_type)
    
    if keyword:
        # 在标题和作者中搜索关键词
        query = query.filter(
            db.or_(
                Achievement.title.ilike(f'%{keyword}%'),
                Achievement.authors.ilike(f'%{keyword}%'),
                Achievement.description.ilike(f'%{keyword}%')
            )
        )
    
    # 如果需要只返回当前用户的成果，并且用户已登录
    if only_mine and request.headers.get('Authorization'):
        try:
            # 从JWT中获取用户ID
            current_user_id = get_jwt_identity()
            if current_user_id:
                query = query.filter_by(user_id=current_user_id)
        except Exception as e:
            logging.error(f"获取用户ID时出错: {e}")
    
    # 执行分页查询
    pagination = query.order_by(Achievement.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    achievements = pagination.items
    total = pagination.total
    
    return jsonify({
        'items': [achievement.to_dict() for achievement in achievements],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

@api.route('/achievements/<int:id>', methods=['GET'])
@jwt_required()
def get_achievement(id):
    """获取指定ID的成果"""
    current_user_id = get_jwt_identity()
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    achievement = Achievement.query.get(id)
    if not achievement:
        return not_found('成果不存在')
    
    if achievement.user_id != current_user_id:
        return unauthorized('无权访问此成果')
    
    return jsonify(achievement.to_dict())

@api.route('/achievements', methods=['POST'])
@jwt_required()
def create_achievement():
    """创建新成果"""
    current_user_id = get_jwt_identity()
    
    # 获取请求数据
    data = request.get_json() or {}
    logging.info(f"创建成果请求数据: {data}")
    logging.info(f"当前用户ID: {current_user_id}, 类型: {type(current_user_id)}")
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    # 检查必填字段
    if 'title' not in data:
        return bad_request('成果标题是必填项')
    
    # 创建新的成果记录
    achievement = Achievement(
        user_id=current_user_id,
        title=str(data.get('title', '')),
        achievement_type=str(data.get('achievement_type', '其他')),
        authors=str(data.get('authors', '')),
        description=str(data.get('description', '')),
        url=str(data.get('url', ''))
    )
    
    # 处理日期字段
    if 'publish_date' in data and data['publish_date']:
        try:
            # 将字符串转换为日期对象
            # 尝试多种日期格式
            date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']
            publish_date = None
            
            for date_format in date_formats:
                try:
                    publish_date = datetime.strptime(str(data['publish_date']), date_format).date()
                    break
                except ValueError:
                    continue
            
            if publish_date:
                achievement.publish_date = publish_date
            else:
                # 如果无法解析日期，则设置为当前日期
                achievement.publish_date = date.today()
        except Exception as e:
            logging.error(f"处理发布日期时出错: {e}")
            achievement.publish_date = date.today()
    else:
        # 如果没有提供日期，默认使用当前日期
        achievement.publish_date = date.today()
    
    # 处理文件路径和原始文件名
    if 'file_path' in data:
        achievement.file_path = str(data.get('file_path', ''))
    if 'original_file_name' in data:
        achievement.original_file_name = str(data.get('original_file_name', ''))
    
    # 处理附加文件
    if 'additional_files' in data:
        if isinstance(data['additional_files'], list):
            processed_files = []
            for file_info in data['additional_files']:
                if isinstance(file_info, dict):
                    processed_file = {}
                    for key, value in file_info.items():
                        processed_file[key] = str(value) if value is not None else ''
                    processed_files.append(processed_file)
            achievement.additional_files = json.dumps(processed_files)
        else:
            # 如果不是列表，则设置为空列表
            achievement.additional_files = json.dumps([])
    
    try:
        db.session.add(achievement)
        db.session.commit()
        return jsonify(achievement.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"创建成果时发生错误: {e}")
        return jsonify({"msg": f"创建成果失败: {str(e)}"}), 500

@api.route('/achievements/<int:id>', methods=['PUT'])
@jwt_required()
def update_achievement(id):
    """更新指定ID的成果"""
    current_user_id = get_jwt_identity()
    logging.info(f"更新成果 ID {id} 请求")
    logging.info(f"当前用户ID: {current_user_id}, 类型: {type(current_user_id)}")
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    achievement = Achievement.query.get(id)
    if not achievement:
        return not_found('成果不存在')
    
    if achievement.user_id != current_user_id:
        return unauthorized('无权修改此成果')
    
    data = request.get_json() or {}
    logging.info(f"更新成果请求数据: {data}")
    
    # 更新字段
    if 'title' in data:
        achievement.title = str(data['title'])
    if 'achievement_type' in data:
        achievement.achievement_type = str(data['achievement_type'])
    if 'authors' in data:
        achievement.authors = str(data['authors'])
    if 'publish_date' in data and data['publish_date']:
        try:
            # 尝试多种日期格式
            date_formats = ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']
            publish_date = None
            
            for date_format in date_formats:
                try:
                    publish_date = datetime.strptime(str(data['publish_date']), date_format).date()
                    break
                except ValueError:
                    continue
            
            if publish_date:
                achievement.publish_date = publish_date
            else:
                # 如果无法解析日期，则设置为当前日期
                achievement.publish_date = date.today()
        except Exception as e:
            logging.error(f"处理发布日期时出错: {e}")
            achievement.publish_date = date.today()
    if 'description' in data:
        achievement.description = str(data['description'])
    if 'url' in data:
        achievement.url = str(data['url'])
    if 'file_path' in data:
        achievement.file_path = str(data['file_path'])
    if 'original_file_name' in data:
        achievement.original_file_name = str(data['original_file_name'])
    
    # 处理附加文件
    if 'additional_files' in data:
        if isinstance(data['additional_files'], list):
            # 确保列表中的每个元素都是字典，并且字典中的值都是字符串
            processed_files = []
            for file_info in data['additional_files']:
                if isinstance(file_info, dict):
                    processed_file = {}
                    for key, value in file_info.items():
                        processed_file[key] = str(value) if value is not None else ''
                    processed_files.append(processed_file)
            achievement.additional_files = json.dumps(processed_files)
        else:
            # 如果不是列表，则设置为空列表
            achievement.additional_files = json.dumps([])
    
    try:
        db.session.commit()
        return jsonify(achievement.to_dict())
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新成果时发生错误: {e}")
        return jsonify({"msg": f"更新成果失败: {str(e)}"}), 500

@api.route('/achievements/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_achievement(id):
    """删除指定ID的成果"""
    current_user_id = get_jwt_identity()
    
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        try:
            current_user_id = int(current_user_id)
        except ValueError:
            return jsonify({"msg": "无效的用户ID"}), 400
    
    achievement = Achievement.query.get(id)
    if not achievement:
        return not_found('成果不存在')
    
    if achievement.user_id != current_user_id:
        return unauthorized('无权删除此成果')
    
    db.session.delete(achievement)
    db.session.commit()
    
    return jsonify({'message': '成果已删除'}) 