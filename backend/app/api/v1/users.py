from flask import jsonify, request, current_app
from sqlalchemy import text
from flask_jwt_extended import jwt_required, current_user
from app.api.v1 import api
from app.models import db, User, Role
from app.api.v1.errors import bad_request, not_found, forbidden
from app.utils.decorators import admin_required


@api.route('/users', methods=['GET'])
@jwt_required()
def get_users_list():
    return jsonify([user.to_dict() for user in User.query.order_by(User.id).all()])


@api.route('/users/current', methods=['GET'])
@jwt_required()
def get_current_user_info():
    return jsonify(current_user.to_dict())


@api.route('/users/<int:id>', methods=['GET'])
@jwt_required()
def get_user_by_id(id):
    return jsonify(User.query.get_or_404(id).to_dict())


@api.route('/roles', methods=['GET'])
@admin_required
def get_roles():
    return jsonify([{'name': role.name, 'permissions': role.permissions}
                    for role in Role.query.order_by(Role.permissions).all()])


@api.route('/users/<int:id>/role', methods=['PUT'])
@admin_required
def set_user_role(id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('role'), str):
        return bad_request('必须提供角色名称')
    if data['role'] not in ('User', 'Moderator', 'Administrator'):
        return bad_request('不支持的角色')
    # An update obtains a writer lock on SQLite and a row lock on PostgreSQL/MySQL.
    # Recheck the actor after serialisation so concurrent cross-demotions cannot remove every admin.
    db.session.execute(text("UPDATE roles SET permissions = permissions WHERE name = 'Administrator'"))
    db.session.expire_all()
    if not current_user.is_administrator():
        db.session.rollback()
        return forbidden('管理员角色已变更，请刷新页面')
    user = User.query.get(id)
    if user is None:
        return not_found('用户不存在')
    role = Role.query.filter_by(name=data['role']).first()
    if role is None:
        return bad_request('角色尚未初始化')
    if current_user.id == id and role.name != 'Administrator':
        return forbidden('不能降低自己的管理员角色，请由另一位管理员操作')
    previous = user.role.name if user.role else None
    user.role = role
    db.session.commit()
    current_app.logger.info('role_changed actor_id=%s user_id=%s previous=%s role=%s',
                            current_user.id, user.id, previous, role.name)
    return jsonify(user=user.to_dict())
