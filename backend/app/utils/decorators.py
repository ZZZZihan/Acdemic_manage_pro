from functools import wraps
from flask import jsonify
from flask_jwt_extended import current_user, jwt_required
from app.models import Permission


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated(*args, **kwargs):
            if not current_user.can(permission):
                return jsonify(message='没有权限执行此操作'), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
