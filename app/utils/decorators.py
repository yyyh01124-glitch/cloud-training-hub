from functools import wraps
from flask import abort, request
from flask_login import current_user


def role_required(*roles):
    """限制路由访问角色. Usage: @role_required('admin', 'teacher')"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            if current_user.role.name not in roles:
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def teacher_or_admin(f):
    """教师或管理员可访问"""
    @wraps(f)
    @role_required('admin', 'teacher')
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
