class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    achievement_type = db.Column(db.String(50), default='其他')
    authors = db.Column(db.String(255))
    publish_date = db.Column(db.String(50))
    description = db.Column(db.Text)
    url = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    original_file_name = db.Column(db.String(255))
    additional_files = db.Column(db.Text)  # 存储JSON格式的附加文件信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', back_populates='achievements')
    
    def to_dict(self):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'achievement_type': self.achievement_type,
            'authors': self.authors,
            'publish_date': self.publish_date,
            'description': self.description,
            'url': self.url,
            'file_path': self.file_path,
            'original_file_name': self.original_file_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 解析附加文件信息
        if self.additional_files:
            try:
                import json
                data['additional_files'] = json.loads(self.additional_files)
            except:
                data['additional_files'] = []
        else:
            data['additional_files'] = []
            
        return data 