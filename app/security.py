from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    roles = {r.lower() for r in roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            user_role = (current_user.role or "").lower()
            if user_role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
