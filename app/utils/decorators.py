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


def send_notification(user_id, notif_type, title, content='', link=''):
    """发送站内通知"""
    try:
        from app.extensions import db
        from app.models import Notification
        n = Notification(user_id=user_id, type=notif_type, title=title, content=content, link=link)
        db.session.add(n)
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'send_notification failed: {e}')


def log_activity(action, module='', target_type='', target_id=0, detail=None):
    """记录关键操作到 system_logs 表"""
    try:
        from flask_login import current_user
        from app.extensions import db
        from app.models import SystemLog
        log = SystemLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            module=module,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
            ip_address=request.remote_addr or ''
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f'log_activity failed: {e}')
