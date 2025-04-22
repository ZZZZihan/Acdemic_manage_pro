from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from datetime import datetime
import os

from app.api.v1 import api
from app.models import db
from app.models.project import Project, ProjectMember, ProjectFile
from app.models.user import User
from app.api.v1.errors import bad_request, not_found

@api.route('/projects', methods=['GET'])
def get_projects():
    """获取项目列表"""
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    # 过滤参数
    status = request.args.get('status')
    priority = request.args.get('priority')
    query_term = request.args.get('q', '')
    
    # 基本查询
    query = Project.query
    
    # 应用筛选条件
    if status:
        query = query.filter(Project.status == status)
    if priority:
        query = query.filter(Project.priority == priority)
    if query_term:
        query = query.filter(Project.name.ilike(f'%{query_term}%'))
    
    # 排序（默认按创建时间降序）
    query = query.order_by(desc(Project.created_at))
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page)
    projects = pagination.items
    
    return jsonify({
        'projects': [project.to_dict() for project in projects],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@api.route('/projects/<int:id>', methods=['GET'])
def get_project(id):
    """获取单个项目详情"""
    project = Project.query.get_or_404(id)
    return jsonify(project.to_dict())

@api.route('/projects', methods=['POST'])
@jwt_required()
def create_project():
    """创建新项目"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return bad_request('用户不存在')
    
    # 解析请求数据
    data = request.get_json() or {}
    required_fields = ['name']
    
    # 验证必填字段
    for field in required_fields:
        if field not in data:
            return bad_request(f'缺少必填字段: {field}')
    
    # 创建项目
    project = Project(
        name=data.get('name'),
        description=data.get('description', ''),
        status=data.get('status', '进行中'),
        priority=data.get('priority', '中'),
        creator_id=current_user_id
    )
    
    # 处理日期字段
    if data.get('start_date'):
        try:
            project.start_date = datetime.fromisoformat(data.get('start_date'))
        except (ValueError, TypeError):
            return bad_request('开始日期格式无效')
    
    if data.get('end_date'):
        try:
            project.end_date = datetime.fromisoformat(data.get('end_date'))
        except (ValueError, TypeError):
            return bad_request('结束日期格式无效')
    
    # 创建者自动成为项目成员
    creator_member = ProjectMember(
        user_id=current_user_id,
        role='负责人'
    )
    project.members.append(creator_member)
    
    # 处理其他成员
    if 'members' in data and isinstance(data['members'], list):
        for member_data in data['members']:
            # 检查成员有效性
            member_id = member_data.get('user_id')
            if not member_id or not User.query.get(member_id):
                continue
                
            # 创建成员关联
            member = ProjectMember(
                user_id=member_id,
                role=member_data.get('role', '成员')
            )
            project.members.append(member)
    
    # 保存到数据库
    db.session.add(project)
    db.session.commit()
    
    return jsonify(project.to_dict()), 201

@api.route('/projects/<int:id>', methods=['PUT'])
@jwt_required()
def update_project(id):
    """更新项目信息"""
    # 获取当前用户
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return bad_request('用户不存在')
        
    # 查找项目
    project = Project.query.get_or_404(id)
    
    # 验证权限（只有创建者或项目成员可以修改）
    is_creator = project.creator_id == current_user_id
    is_member = any(member.user_id == current_user_id for member in project.members)
    
    if not (is_creator or is_member):
        return jsonify({'msg': '无权限修改此项目'}), 403
    
    # 解析请求数据
    data = request.get_json() or {}
    
    # 更新基本信息
    if 'name' in data:
        project.name = data['name']
    if 'description' in data:
        project.description = data['description']
    if 'status' in data:
        project.status = data['status']
    if 'priority' in data:
        project.priority = data['priority']
    
    # 处理日期
    if 'start_date' in data:
        if data['start_date']:
            try:
                project.start_date = datetime.fromisoformat(data['start_date'])
            except (ValueError, TypeError):
                return bad_request('开始日期格式无效')
        else:
            project.start_date = None
            
    if 'end_date' in data:
        if data['end_date']:
            try:
                project.end_date = datetime.fromisoformat(data['end_date'])
            except (ValueError, TypeError):
                return bad_request('结束日期格式无效')
        else:
            project.end_date = None
    
    # 如果是创建者，处理成员更新
    if is_creator and 'members' in data and isinstance(data['members'], list):
        # 保存创建者成员关系
        creator_member = next((m for m in project.members if m.user_id == current_user_id), None)
        
        # 清除现有成员（除了创建者）
        for member in list(project.members):
            if member.user_id != current_user_id:
                db.session.delete(member)
        
        # 添加新成员
        for member_data in data['members']:
            member_id = member_data.get('user_id')
            # 不添加创建者（已经存在）
            if member_id and member_id != current_user_id and User.query.get(member_id):
                member = ProjectMember(
                    project=project,
                    user_id=member_id,
                    role=member_data.get('role', '成员')
                )
                db.session.add(member)
    
    # 保存更新
    db.session.commit()
    
    return jsonify(project.to_dict())

@api.route('/projects/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_project(id):
    """删除项目"""
    # 获取当前用户
    current_user_id = get_jwt_identity()
    print(f"删除项目 - 项目ID: {id}, 用户ID: {current_user_id}")
    
    # 尝试将用户ID转换为整数
    try:
        if isinstance(current_user_id, str) and current_user_id.isdigit():
            current_user_id = int(current_user_id)
    except (ValueError, TypeError):
        print(f"用户ID类型转换失败: {current_user_id}, 类型: {type(current_user_id)}")
    
    # 查找项目
    project = Project.query.get_or_404(id)
    print(f"项目信息 - 名称: {project.name}, 创建者ID: {project.creator_id}")
    
    # 验证权限（只有创建者可以删除）
    print(f"比较创建者ID: {project.creator_id} vs 当前用户ID: {current_user_id}")
    print(f"创建者判断结果: {project.creator_id == current_user_id}")
    
    if project.creator_id != current_user_id:
        print(f"权限验证失败: 用户 {current_user_id} 尝试删除项目 {id}，但创建者是 {project.creator_id}")
        return jsonify({'msg': '只有项目创建者可以删除项目'}), 403
    
    # 删除项目
    db.session.delete(project)
    db.session.commit()
    print(f"项目 {id} 已成功删除")
    
    return jsonify({'msg': '项目已删除'})

@api.route('/projects/user', methods=['GET'])
@jwt_required()
def get_user_projects():
    """获取当前用户参与的项目"""
    current_user_id = get_jwt_identity()
    
    # 查询用户创建的项目
    created_projects = Project.query.filter_by(creator_id=current_user_id).all()
    
    # 查询用户参与的项目（但不是创建者的）
    joined_projects_ids = db.session.query(ProjectMember.project_id).filter(
        ProjectMember.user_id == current_user_id,
        Project.creator_id != current_user_id
    ).join(Project, ProjectMember.project_id == Project.id).all()
    
    joined_projects_ids = [id[0] for id in joined_projects_ids]
    joined_projects = Project.query.filter(Project.id.in_(joined_projects_ids)).all() if joined_projects_ids else []
    
    return jsonify({
        'created': [project.to_dict() for project in created_projects],
        'joined': [project.to_dict() for project in joined_projects]
    })

@api.route('/projects/<int:project_id>/files', methods=['GET'])
@jwt_required()
def get_project_files(project_id):
    """获取项目的文件列表"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 验证权限（应该是项目成员或创建者）
    is_creator = project.creator_id == current_user_id
    
    # 通过查询数据库判断是否为成员
    member_query = ProjectMember.query.filter_by(
        project_id=project_id, 
        user_id=current_user_id
    ).first()
    
    is_member = member_query is not None
    
    print(f"验证权限 - 用户ID: {current_user_id}, 创建者: {is_creator}, 成员: {is_member}")
    
    if not (is_creator or is_member):
        return jsonify({'msg': '无权访问此项目的文件'}), 403
    
    # 获取项目文件列表
    files = ProjectFile.query.filter_by(project_id=project_id).order_by(desc(ProjectFile.created_at)).all()
    
    return jsonify([file.to_dict() for file in files])

@api.route('/projects/<int:project_id>/files', methods=['POST'])
@jwt_required()
def add_project_file(project_id):
    """添加文件到项目"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 验证权限（应该是项目成员或创建者）
    is_creator = project.creator_id == current_user_id
    is_member = any(member.user_id == current_user_id for member in project.members)
    
    if not (is_creator or is_member):
        return jsonify({'msg': '无权为此项目添加文件'}), 403
    
    # 解析请求数据
    data = request.get_json() or {}
    
    # 验证必填字段
    if 'file_path' not in data:
        return bad_request('缺少文件路径')
    
    # 创建文件记录
    project_file = ProjectFile(
        project_id=project_id,
        file_path=data.get('file_path'),
        original_name=data.get('original_name'),
        file_size=data.get('file_size'),
        file_type=data.get('file_type'),
        uploader_id=current_user_id
    )
    
    # 保存到数据库
    db.session.add(project_file)
    db.session.commit()
    
    return jsonify(project_file.to_dict()), 201

@api.route('/projects/<int:project_id>/files/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_project_file(project_id, file_id):
    """从项目中删除文件"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 查找文件
    project_file = ProjectFile.query.get_or_404(file_id)
    
    # 确认文件是否属于该项目
    if project_file.project_id != project_id:
        return bad_request('文件不属于该项目')
    
    # 验证权限（只有创建者或上传者可以删除）
    is_creator = project.creator_id == current_user_id
    is_uploader = project_file.uploader_id == current_user_id
    
    if not (is_creator or is_uploader):
        return jsonify({'msg': '无权删除此文件'}), 403
    
    # 删除文件记录
    db.session.delete(project_file)
    db.session.commit()
    
    return jsonify({'msg': '文件已从项目中删除'})

# 可以考虑添加物理删除文件的API，但请确保有足够的安全检查
@api.route('/projects/<int:project_id>/files/<int:file_id>/physical', methods=['DELETE'])
@jwt_required()
def delete_project_file_physical(project_id, file_id):
    """物理删除项目文件（同时删除文件记录和实际文件）"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找项目
    project = Project.query.get_or_404(project_id)
    
    # 查找文件
    project_file = ProjectFile.query.get_or_404(file_id)
    
    # 确认文件是否属于该项目
    if project_file.project_id != project_id:
        return bad_request('文件不属于该项目')
    
    # 验证权限（只有创建者或上传者可以删除）
    is_creator = project.creator_id == current_user_id
    is_uploader = project_file.uploader_id == current_user_id
    
    if not (is_creator or is_uploader):
        return jsonify({'msg': '无权删除此文件'}), 403
    
    # 尝试物理删除文件
    try:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], project_file.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        current_app.logger.error(f"删除文件时出错: {str(e)}")
        # 即使文件删除失败，我们仍然可以继续删除数据库记录
    
    # 删除文件记录
    db.session.delete(project_file)
    db.session.commit()
    
    return jsonify({'msg': '文件已完全删除'}) 