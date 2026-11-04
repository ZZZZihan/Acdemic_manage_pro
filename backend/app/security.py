"""Authentication helpers.

JWT is required at the edge of protected views. Admin checks use the role
bit stored on the user, not a second hard-coded account list.
"""
from functools import wraps

from flask import g, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1.errors import forbidden, unauthorized
from app.audit import emit
from app.models import User


def _load_user():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return User.query.get(user_id)


def member_required(fn):
    """Any authenticated account."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = _load_user()
        if user is None:
            return unauthorized("用户不存在或登录态无效")
        g.actor = user
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    """Authenticated administrator only."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = _load_user()
        if user is None:
            return unauthorized("用户不存在或登录态无效")
        g.actor = user
        if not user.is_administrator():
            emit(
                "permission_denied",
                actor_id=user.id,
                outcome="denied",
                required_role="Administrator",
            )
            return forbidden("需要管理员权限")
        return fn(*args, **kwargs)

    return wrapper


def directory_view(user, viewer):
    """Member directory payload. Email stays with the subject and administrators."""
    data = user.to_dict()
    if viewer is None or (viewer.id != user.id and not viewer.is_administrator()):
        data.pop("email", None)
        data.pop("about_me", None)
        data.pop("location", None)
        data.pop("last_seen", None)
    return data


def request_actor_id():
    actor = getattr(g, "actor", None)
    if actor is not None:
        return actor.id
    if not request:
        return None
    return None
