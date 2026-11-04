from flask import g, jsonify
from flask_jwt_extended import jwt_required

from app.api.v1 import api
from app.models.user import User
from app.api.v1.errors import unauthorized
from app.security import directory_view, member_required

@api.route('/users', methods=['GET'])
@member_required
def get_users_list():
    """Authenticated directory. Email is limited to the subject and administrators."""
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([directory_view(user, g.actor) for user in users])

@api.route('/users/current', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """获取当前登录用户的信息"""
    from app.security import _load_user

    user = _load_user()
    if user is None:
        return unauthorized('用户不存在')
    return jsonify(user.to_dict())

@api.route('/users/<int:id>', methods=['GET'])
@member_required
def get_user_by_id(id):
    """获取单个用户的详情"""
    user = User.query.get_or_404(id)
    return jsonify(directory_view(user, g.actor))
