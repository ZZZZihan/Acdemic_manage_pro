from datetime import datetime
from app.models import db

class TechSummary(db.Model):
    __tablename__ = 'tech_summaries'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    content = db.Column(db.Text)
    summary_type = db.Column(db.String(64), index=True)  # 技术总结类型，如算法、工具、方法等
    tags = db.Column(db.String(256))  # 标签，以逗号分隔
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 文件附件相关字段
    file_path = db.Column(db.String(256))
    original_file_name = db.Column(db.String(256))
    
    # 来源URL
    source_url = db.Column(db.String(512))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'summary_type': self.summary_type,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id,
            'file_path': self.file_path,
            'original_file_name': self.original_file_name,
            'source_url': self.source_url
        }
    
    def __repr__(self):
        return f'<TechSummary {self.title}>' 