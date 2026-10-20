from datetime import datetime
from flask import jsonify
from app.models import AuthSession, User


def configure_jwt(jwt):
    def failure(message, code):
        return jsonify(message=message, code=code), 401

    @jwt.unauthorized_loader
    def missing_token(reason):
        return failure('请先登录', 'authentication_required')

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return failure('登录凭证无效，请重新登录', 'token_invalid')

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return failure('登录凭证已过期', 'token_expired')

    @jwt.revoked_token_loader
    def revoked_token(header, payload):
        return failure('登录会话已失效，请重新登录', 'session_revoked')

    @jwt.token_in_blocklist_loader
    def revoked(header, payload):
        sid = payload.get('sid')
        if not isinstance(sid, str):
            return True
        session = AuthSession.query.get(sid)
        return (session is None or session.revoked_at is not None
                or session.expires_at <= datetime.utcnow()
                or str(session.user_id) != payload.get('sub'))

    @jwt.user_lookup_loader
    def lookup_user(header, payload):
        identity = payload.get('sub')
        if not isinstance(identity, str) or not identity.isdecimal() or len(identity) > 18:
            return None
        return User.query.get(int(identity))

    @jwt.user_lookup_error_loader
    def missing_user(header, payload):
        return failure('用户不存在，请重新登录', 'user_not_found')
