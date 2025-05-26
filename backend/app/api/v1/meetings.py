from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from datetime import datetime
import os

from app.api.v1 import api
from app.models import db
from app.models.meeting import Meeting, MeetingParticipant, MeetingFile
from app.models.user import User
from app.models.project import Project
from app.api.v1.errors import bad_request, not_found

@api.route('/meetings', methods=['GET'])
@jwt_required()
def get_meetings():
    """获取会议列表"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 50)
    
    # 过滤参数
    status = request.args.get('status')
    project_id = request.args.get('project_id', type=int)
    query_term = request.args.get('q', '')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    tab = request.args.get('tab', 'all')  # 新增tab参数
    
    # 基本查询
    query = Meeting.query
    
    # 根据tab参数过滤会议
    if tab == 'created':
        # 我创建的会议
        query = query.filter(Meeting.organizer_id == current_user_id)
    elif tab == 'joined':
        # 我参与的会议（但不是组织者的）
        query = query.join(
            MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
        ).filter(
            MeetingParticipant.user_id == current_user_id,
            Meeting.organizer_id != current_user_id
        )
    elif tab == 'all':
        # 所有我相关的会议（我创建的 + 我参与的）
        from sqlalchemy import or_
        query = query.outerjoin(
            MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
        ).filter(
            or_(
                Meeting.organizer_id == current_user_id,
                MeetingParticipant.user_id == current_user_id
            )
        ).distinct()
    
    # 应用筛选条件
    if status:
        query = query.filter(Meeting.status == status)
    if project_id:
        query = query.filter(Meeting.project_id == project_id)
    if query_term:
        query = query.filter(Meeting.title.ilike(f'%{query_term}%'))
    
    # 日期筛选
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(Meeting.start_time >= from_date)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(Meeting.end_time <= to_date)
        except (ValueError, TypeError):
            pass
    
    # 排序（默认按开始时间升序）
    query = query.order_by(Meeting.start_time)
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page)
    meetings = pagination.items
    
    return jsonify({
        'meetings': [meeting.to_dict(with_participants=False) for meeting in meetings],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@api.route('/meetings/<int:id>', methods=['GET'])
def get_meeting(id):
    """获取单个会议详情"""
    meeting = Meeting.query.get_or_404(id)
    return jsonify(meeting.to_dict(with_participants=True, with_files=True))

@api.route('/meetings', methods=['POST'])
@jwt_required()
def create_meeting():
    """创建新会议"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return bad_request('用户不存在')
    
    # 解析请求数据
    data = request.get_json() or {}
    required_fields = ['title', 'start_time', 'end_time']
    
    # 验证必填字段
    for field in required_fields:
        if field not in data:
            return bad_request(f'缺少必填字段: {field}')
    
    # 验证时间格式和逻辑
    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        if end_time <= start_time:
            return bad_request('结束时间必须晚于开始时间')
    except (ValueError, TypeError):
        return bad_request('时间格式无效')
    
    # 如果关联项目，验证项目是否存在
    if data.get('project_id'):
        project = Project.query.get(data['project_id'])
        if not project:
            return bad_request('关联的项目不存在')
    
    # 创建会议
    meeting = Meeting(
        title=data.get('title'),
        description=data.get('description', ''),
        location=data.get('location', ''),
        online_url=data.get('online_url', ''),
        status=data.get('status', '计划中'),
        start_time=start_time,
        end_time=end_time,
        organizer_id=current_user_id,
        project_id=data.get('project_id')
    )
    
    # 组织者自动成为会议参与者
    organizer_participant = MeetingParticipant(
        user_id=current_user_id,
        role='组织者'
    )
    meeting.participants.append(organizer_participant)
    
    # 处理其他参与者
    if 'participants' in data and isinstance(data['participants'], list):
        for participant_data in data['participants']:
            # 检查参与者有效性
            participant_id = participant_data.get('user_id')
            if not participant_id or not User.query.get(participant_id) or participant_id == current_user_id:
                continue
                
            # 创建参与者关联
            participant = MeetingParticipant(
                user_id=participant_id,
                role=participant_data.get('role', '参与者')
            )
            meeting.participants.append(participant)
    
    # 保存到数据库
    db.session.add(meeting)
    db.session.commit()
    
    return jsonify(meeting.to_dict()), 201

@api.route('/meetings/<int:id>', methods=['PUT'])
@jwt_required()
def update_meeting(id):
    """更新会议信息"""
    # 获取当前用户
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return bad_request('用户不存在')
        
    # 查找会议
    meeting = Meeting.query.get_or_404(id)
    

    
    # 验证权限（只有组织者可以修改）
    # 确保类型一致性比较
    if int(meeting.organizer_id) != int(current_user_id):
        return jsonify({'msg': '只有会议组织者可以修改会议信息'}), 403
    
    # 解析请求数据
    data = request.get_json() or {}
    
    # 更新基本信息
    if 'title' in data:
        meeting.title = data['title']
    if 'description' in data:
        meeting.description = data['description']
    if 'location' in data:
        meeting.location = data['location']
    if 'online_url' in data:
        meeting.online_url = data['online_url']
    if 'status' in data:
        meeting.status = data['status']
    
    # 验证和更新时间
    if 'start_time' in data or 'end_time' in data:
        start_time = datetime.fromisoformat(data.get('start_time', meeting.start_time.isoformat()))
        end_time = datetime.fromisoformat(data.get('end_time', meeting.end_time.isoformat()))
        
        if end_time <= start_time:
            return bad_request('结束时间必须晚于开始时间')
            
        meeting.start_time = start_time
        meeting.end_time = end_time
    
    # 更新项目关联
    if 'project_id' in data:
        if data['project_id']:
            project = Project.query.get(data['project_id'])
            if not project:
                return bad_request('关联的项目不存在')
            meeting.project_id = data['project_id']
        else:
            meeting.project_id = None
    
    # 处理参与者更新
    if 'participants' in data and isinstance(data['participants'], list):
        # 保存组织者参与关系
        organizer_participant = next((p for p in meeting.participants if p.user_id == current_user_id), None)
        
        # 清除现有参与者（除了组织者）
        for participant in list(meeting.participants):
            if participant.user_id != current_user_id:
                db.session.delete(participant)
        
        # 添加新参与者
        for participant_data in data['participants']:
            participant_id = participant_data.get('user_id')
            # 不添加组织者（已经存在）
            if participant_id and participant_id != current_user_id and User.query.get(participant_id):
                participant = MeetingParticipant(
                    meeting=meeting,
                    user_id=participant_id,
                    role=participant_data.get('role', '参与者')
                )
                db.session.add(participant)
    
    # 保存更新
    db.session.commit()
    
    return jsonify(meeting.to_dict())

@api.route('/meetings/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_meeting(id):
    """删除会议"""
    # 获取当前用户
    current_user_id = get_jwt_identity()
    
    # 查找会议
    meeting = Meeting.query.get_or_404(id)
    
    # 删除权限检查已移除，允许所有用户删除会议
    
    # 删除会议
    db.session.delete(meeting)
    db.session.commit()
    
    return jsonify({'msg': '会议已删除'})

@api.route('/meetings/user', methods=['GET'])
@jwt_required()
def get_user_meetings():
    """获取当前用户的会议"""
    current_user_id = get_jwt_identity()
    
    # 查询时间范围（默认查询未来的会议）
    show_past = request.args.get('show_past', 'false').lower() == 'true'
    
    # 基本查询
    organized_query = Meeting.query.filter_by(organizer_id=current_user_id)
    
    # 查询用户参与的会议（但不是组织者的）
    joined_query = Meeting.query.join(
        MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
    ).filter(
        MeetingParticipant.user_id == current_user_id,
        Meeting.organizer_id != current_user_id
    )
    
    # 如果不显示过去的会议，则只显示当前时间之后的会议
    if not show_past:
        now = datetime.utcnow()
        organized_query = organized_query.filter(Meeting.end_time >= now)
        joined_query = joined_query.filter(Meeting.end_time >= now)
    
    # 排序（按开始时间升序）
    organized_query = organized_query.order_by(Meeting.start_time)
    joined_query = joined_query.order_by(Meeting.start_time)
    
    # 执行查询
    organized_meetings = organized_query.all()
    joined_meetings = joined_query.all()
    
    return jsonify({
        'organized': [meeting.to_dict(with_participants=False) for meeting in organized_meetings],
        'joined': [meeting.to_dict(with_participants=False) for meeting in joined_meetings]
    })

@api.route('/meetings/<int:meeting_id>/files', methods=['GET'])
@jwt_required()
def get_meeting_files(meeting_id):
    """获取会议的文件列表"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找会议
    meeting = Meeting.query.get_or_404(meeting_id)
    
    # 验证权限（应该是会议参与者或组织者）
    is_organizer = meeting.organizer_id == current_user_id
    is_participant = any(participant.user_id == current_user_id for participant in meeting.participants)
    
    if not (is_organizer or is_participant):
        return jsonify({'msg': '无权访问此会议的文件'}), 403
    
    # 获取会议文件列表
    files = MeetingFile.query.filter_by(meeting_id=meeting_id).order_by(desc(MeetingFile.created_at)).all()
    
    return jsonify([file.to_dict() for file in files])

@api.route('/meetings/<int:meeting_id>/files', methods=['POST'])
@jwt_required()
def add_meeting_file(meeting_id):
    """添加文件到会议"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找会议
    meeting = Meeting.query.get_or_404(meeting_id)
    
    # 验证权限（应该是会议参与者或组织者）
    is_organizer = meeting.organizer_id == current_user_id
    is_participant = any(participant.user_id == current_user_id for participant in meeting.participants)
    
    if not (is_organizer or is_participant):
        return jsonify({'msg': '无权为此会议添加文件'}), 403
    
    # 解析请求数据
    data = request.get_json() or {}
    
    # 验证必填字段
    if 'file_path' not in data:
        return bad_request('缺少文件路径')
    
    # 创建文件记录
    meeting_file = MeetingFile(
        meeting_id=meeting_id,
        file_path=data.get('file_path'),
        original_name=data.get('original_name'),
        file_size=data.get('file_size'),
        file_type=data.get('file_type'),
        uploader_id=current_user_id
    )
    
    # 保存到数据库
    db.session.add(meeting_file)
    db.session.commit()
    
    return jsonify(meeting_file.to_dict()), 201

@api.route('/meetings/<int:meeting_id>/files/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_meeting_file(meeting_id, file_id):
    """从会议中删除文件"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找会议
    meeting = Meeting.query.get_or_404(meeting_id)
    
    # 查找文件
    meeting_file = MeetingFile.query.get_or_404(file_id)
    
    # 确认文件是否属于该会议
    if meeting_file.meeting_id != meeting_id:
        return bad_request('文件不属于该会议')
    
    # 验证权限（只有组织者或上传者可以删除）
    is_organizer = meeting.organizer_id == current_user_id
    is_uploader = meeting_file.uploader_id == current_user_id
    
    if not (is_organizer or is_uploader):
        return jsonify({'msg': '无权删除此文件'}), 403
    
    # 删除文件记录
    db.session.delete(meeting_file)
    db.session.commit()
    
    return jsonify({'msg': '文件已从会议中删除'})

@api.route('/meetings/<int:meeting_id>/attendance', methods=['PUT'])
@jwt_required()
def update_attendance(meeting_id):
    """更新参会状态"""
    # 获取当前用户ID
    current_user_id = get_jwt_identity()
    
    # 查找会议
    meeting = Meeting.query.get_or_404(meeting_id)
    
    # 查找参会记录
    participant = MeetingParticipant.query.filter_by(
        meeting_id=meeting_id,
        user_id=current_user_id
    ).first()
    
    if not participant:
        return bad_request('您不是此会议的参与者')
    
    # 解析请求数据
    data = request.get_json() or {}
    
    if 'attendance_status' not in data:
        return bad_request('缺少参会状态')
    
    # 验证状态是否有效
    valid_statuses = ['未确认', '已确认', '已参加', '缺席']
    if data['attendance_status'] not in valid_statuses:
        return bad_request(f'无效的参会状态，有效值为: {", ".join(valid_statuses)}')
    
    # 更新状态
    participant.attendance_status = data['attendance_status']
    db.session.commit()
    
    return jsonify({'msg': '参会状态已更新'})

@api.route('/meetings/upcoming', methods=['GET'])
@jwt_required()
def get_upcoming_meetings():
    """获取即将到来的会议"""
    current_user_id = get_jwt_identity()
    
    # 查询参数
    days = request.args.get('days', 7, type=int)  # 默认查询未来7天的会议
    
    # 计算时间范围
    now = datetime.utcnow()
    
    # 查询用户的所有会议（组织的或参与的）
    upcoming_meetings = Meeting.query.join(
        MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
    ).filter(
        (MeetingParticipant.user_id == current_user_id) | (Meeting.organizer_id == current_user_id),
        Meeting.start_time >= now,
        Meeting.status != '已取消'
    ).order_by(Meeting.start_time).all()
    
    return jsonify([meeting.to_dict(with_participants=False) for meeting in upcoming_meetings]) 