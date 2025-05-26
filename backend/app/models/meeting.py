from datetime import datetime
from app.models import db

class MeetingParticipant(db.Model):
    """会议参与者关联表"""
    __tablename__ = 'meeting_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='参与者')  # 主持人、参与者等
    attendance_status = db.Column(db.String(50), default='未确认')  # 未确认、已确认、已参加、缺席等
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    meeting = db.relationship('Meeting', back_populates='participants')
    user = db.relationship('User', back_populates='meeting_participations')
    
    def to_dict(self):
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'user_id': self.user_id,
            'role': self.role,
            'attendance_status': self.attendance_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class MeetingFile(db.Model):
    """会议文件模型"""
    __tablename__ = 'meeting_files'
    
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # 文件路径
    original_name = db.Column(db.String(255))  # 原始文件名
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    file_type = db.Column(db.String(100))  # 文件类型
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 关系
    meeting = db.relationship('Meeting', back_populates='files')
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_meeting_files')
    
    def to_dict(self):
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'file_path': self.file_path,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploader_id': self.uploader_id,
            'uploader': self.uploader.username if self.uploader else None
        }

class Meeting(db.Model):
    """会议模型"""
    __tablename__ = 'meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))  # 线下会议地点
    online_url = db.Column(db.String(500))  # 线上会议链接
    status = db.Column(db.String(50), default='计划中')  # 计划中、已完成、已取消等
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))  # 会议可以关联到项目（可选）
    
    # 关系
    organizer = db.relationship('User', foreign_keys=[organizer_id], backref='organized_meetings')
    project = db.relationship('Project', backref='meetings')
    participants = db.relationship('MeetingParticipant', back_populates='meeting', cascade='all, delete-orphan')
    files = db.relationship('MeetingFile', back_populates='meeting', cascade='all, delete-orphan')
    
    def to_dict(self, with_participants=True, with_files=False):
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'online_url': self.online_url,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'organizer_id': self.organizer_id,
            'organizer': self.organizer.to_dict() if self.organizer else None,
            # 为了向后兼容，同时提供creator字段
            'creator': self.organizer.to_dict() if self.organizer else None,
            'project_id': self.project_id,
            'project': {
                'id': self.project.id,
                'name': self.project.name
            } if self.project else None
        }
        
        if with_participants:
            data['participants'] = [participant.to_dict() for participant in self.participants]
            
        if with_files:
            data['files'] = [file.to_dict() for file in self.files]
            
        return data 