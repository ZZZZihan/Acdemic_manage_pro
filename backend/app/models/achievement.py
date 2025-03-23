from datetime import datetime
from app.models import db

class Achievement(db.Model):
    __tablename__ = 'achievements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), index=True)
    description = db.Column(db.Text)
    achievement_type = db.Column(db.String(64), index=True)  # 论文、专利、项目等
    authors = db.Column(db.String(256))
    publish_date = db.Column(db.Date)
    url = db.Column(db.String(256))
    file_path = db.Column(db.String(256))
    original_file_name = db.Column(db.String(256))  # 原始文件名
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'achievement_type': self.achievement_type,
            'authors': self.authors,
            'publish_date': self.publish_date.isoformat() if self.publish_date else None,
            'url': self.url,
            'file_path': self.file_path,
            'original_file_name': self.original_file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'user_id': self.user_id
        }
    
    def __repr__(self):
        return f'<Achievement {self.title}>' 