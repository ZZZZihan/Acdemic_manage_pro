from datetime import datetime
from app.models import db


class AuthSession(db.Model):
    """One server-revocable login session shared by its access and refresh JWTs."""
    __tablename__ = 'auth_sessions'
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
