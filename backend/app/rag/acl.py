"""Document visibility. ``lab`` is readable by every member. ``private`` is owner or admin."""


def can_read(scope, owner_id, user):
    if (scope or "lab") != "private":
        return True
    if user is None:
        return False
    if bool(_is_admin(user)):
        return True
    user_id = _user_id(user)
    try:
        return int(owner_id) == int(user_id)
    except (TypeError, ValueError):
        return False


def _is_admin(user):
    if isinstance(user, dict):
        return user.get("is_admin")
    checker = getattr(user, "is_administrator", None)
    if callable(checker):
        return checker()
    return False


def _user_id(user):
    if isinstance(user, dict):
        return user.get("id")
    return getattr(user, "id", None)
