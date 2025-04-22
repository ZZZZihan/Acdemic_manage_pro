from datetime import datetime
from app.models import db

class ProjectMember(db.Model):
    """项目成员关联表"""
    __tablename__ = 'project_members'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='成员')  # 成员、负责人等
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', back_populates='project_memberships')
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None
        }

class ProjectFile(db.Model):
    """项目文件模型"""
    __tablename__ = 'project_files'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)  # 文件路径
    original_name = db.Column(db.String(255))  # 原始文件名
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    file_type = db.Column(db.String(100))  # 文件类型
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 关系
    project = db.relationship('Project', back_populates='files')
    uploader = db.relationship('User', backref='uploaded_files')
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'file_path': self.file_path,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'uploader_id': self.uploader_id,
            'uploader': self.uploader.username if self.uploader else None
        }

class Project(db.Model):
    """项目模型"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='进行中')  # 进行中、已完成、已取消
    priority = db.Column(db.String(50), default='中')    # 高、中、低
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 关系
    creator = db.relationship('User', backref='created_projects')
    members = db.relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    files = db.relationship('ProjectFile', back_populates='project', cascade='all, delete-orphan')
    
    def to_dict(self, with_members=True, with_files=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'creator_id': self.creator_id,
            'creator': self.creator.to_dict() if self.creator else None
        }
        
        if with_members:
            data['members'] = [member.to_dict() for member in self.members]
            
        if with_files:
            data['files'] = [file.to_dict() for file in self.files]
            
        return data 