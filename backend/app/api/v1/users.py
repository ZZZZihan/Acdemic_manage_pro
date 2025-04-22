from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1 import api
from app.models.user import User
from app.api.v1.errors import bad_request, not_found

@api.route('/users', methods=['GET'])
def get_users_list():
    """获取所有用户的列表"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@api.route('/users/current', methods=['GET'])
@jwt_required()
def get_current_user_info():
    """获取当前登录用户的信息"""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    return jsonify(user.to_dict())

@api.route('/users/<int:id>', methods=['GET'])
def get_user_by_id(id):
    """获取单个用户的详情"""
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict()) 