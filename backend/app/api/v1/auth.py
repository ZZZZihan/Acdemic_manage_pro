from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from app.models import db, User
from app.api.v1 import api
from app.api.v1.errors import bad_request, unauthorized

@api.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return bad_request('没有提供数据')
    
    if not all(k in data for k in ('email', 'username', 'password')):
        return bad_request('缺少必要字段')
    
    if User.query.filter_by(email=data['email']).first():
        return bad_request('邮箱已被注册')
    
    if User.query.filter_by(username=data['username']).first():
        return bad_request('用户名已被使用')
    
    user = User(
        email=data['email'],
        username=data['username'],
        password=data['password'],
        name=data.get('name', ''),
        location=data.get('location', '')
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': '注册成功',
        'user': user.to_dict()
    }), 201

@api.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return bad_request('没有提供数据')
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return bad_request('邮箱和密码不能为空')
    
    user = User.query.filter_by(email=email).first()
    if user is None or not user.verify_password(password):
        return unauthorized('邮箱或密码错误')
    
    # 更新最后登录时间
    user.ping()
    
    # 创建访问令牌和刷新令牌
    # 确保identity是字符串类型
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })

@api.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    # 确保identity是字符串类型
    access_token = create_access_token(identity=str(current_user_id))
    return jsonify({'access_token': access_token})

@api.route('/auth/user', methods=['GET'])
@jwt_required()
def get_user():
    current_user_id = get_jwt_identity()
    # 确保user_id是整数
    if isinstance(current_user_id, str):
        current_user_id = int(current_user_id)
    
    user = User.query.get(current_user_id)
    if not user:
        return unauthorized('用户不存在')
    
    return jsonify(user.to_dict())

@api.route('/auth/logout', methods=['POST'])
def logout():
    # 在前端应用中处理令牌的清除
    return jsonify({'message': '成功登出'}) 