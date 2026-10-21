from datetime import datetime
from uuid import uuid4
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt, current_user,
)
from sqlalchemy.exc import IntegrityError
from app.models import db, User, Role, AuthSession
from app.api.v1 import api
from app.api.v1.errors import bad_request, unauthorized


def request_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@api.route('/auth/register', methods=['POST'])
def register():
    data = request_object()
    if not all(k in data for k in ('email', 'username', 'password')):
        return bad_request('缺少必要字段')
    if not all(isinstance(data[k], str) for k in ('email', 'username', 'password')):
        return bad_request('邮箱、用户名和密码必须是字符串')
    email, username, password = data['email'].strip(), data['username'].strip(), data['password']
    if not email or not username or not password.strip():
        return bad_request('邮箱、用户名和密码不能为空')
    if len(email) > 64 or '@' not in email or len(username) > 64 or len(password) < 6 or len(password) > 256:
        return bad_request('请检查邮箱、用户名长度及密码长度（6–256个字符）')
    if any(not isinstance(data.get(k, ''), str) for k in ('name', 'location')):
        return bad_request('姓名和位置必须是字符串')
    if User.query.filter_by(email=email).first():
        return bad_request('邮箱已被注册')
    if User.query.filter_by(username=username).first():
        return bad_request('用户名已被使用')
    role = Role.query.filter_by(name='User').first()
    if role is None:
        return jsonify(message='角色尚未初始化，请联系管理员'), 503
    # Never accept a role or permissions from public registration, including special emails.
    user = User(email=email, username=username, password=password, role=role,
                name=data.get('name', ''), location=data.get('location', ''))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return bad_request('邮箱或用户名已被注册')
    return jsonify(message='注册成功', user=user.to_dict()), 201


@api.route('/auth/login', methods=['POST'])
def login():
    data = request_object()
    email, password = data.get('email'), data.get('password')
    if not isinstance(email, str) or not isinstance(password, str):
        return bad_request('邮箱和密码必须是字符串')
    email = email.strip()
    if not email or not password.strip() or len(password) > 256:
        return bad_request('邮箱或密码格式不正确')
    user = User.query.filter_by(email=email).first()
    if user is None or not user.verify_password(password):
        return unauthorized('邮箱或密码错误')
    if user.role is None:
        return jsonify(message='账号角色尚未分配，请联系管理员'), 403
    session = AuthSession(id=uuid4().hex, user_id=user.id,
                          expires_at=datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'])
    user.last_seen = datetime.utcnow()
    db.session.add(session)
    db.session.commit()
    claims = {'sid': session.id}
    return jsonify(access_token=create_access_token(identity=str(user.id), additional_claims=claims),
                   refresh_token=create_refresh_token(identity=str(user.id), additional_claims=claims),
                   user=user.to_dict())


@api.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    if current_user.role is None:
        return jsonify(message='账号角色尚未分配，请联系管理员'), 403
    return jsonify(access_token=create_access_token(identity=str(current_user.id),
                   additional_claims={'sid': get_jwt()['sid']}), user=current_user.to_dict())


@api.route('/auth/user', methods=['GET'])
@jwt_required()
def get_user():
    return jsonify(current_user.to_dict())


@api.route('/auth/logout', methods=['POST'])
@jwt_required(verify_type=False)
def logout():
    # Accept the refresh token as well so an expired access token does not block logout.
    session = AuthSession.query.get(get_jwt()['sid'])
    session.revoked_at = datetime.utcnow()
    db.session.commit()
    return jsonify(message='成功登出')
