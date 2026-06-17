from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

from app.extensions import db
from app.models import User, LoginLog
from app.utils.decorators import role_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(username=username).first()
        ip = request.remote_addr or ''
        ua = request.headers.get('User-Agent', '')[:500]

        if user and user.check_password(password):
            if not user.is_active:
                flash('账号已被禁用，请联系管理员', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = ip
            user.login_fail_count = 0
            log = LoginLog(user_id=user.id, ip_address=ip, user_agent=ua, is_success=True)
            db.session.add(log)
            db.session.commit()

            flash(f'欢迎回来，{user.real_name}！', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            if user:
                user.login_fail_count = (user.login_fail_count or 0) + 1
                if user.login_fail_count >= 5:
                    user.is_active = False
                    flash('登录失败次数过多，账号已被锁定', 'danger')
                else:
                    remaining = 5 - user.login_fail_count
                    flash(f'用户名或密码错误，还剩 {remaining} 次尝试机会', 'danger')
                log = LoginLog(user_id=user.id, ip_address=ip, user_agent=ua, is_success=False, fail_reason='wrong_password')
                db.session.add(log)
                db.session.commit()
            else:
                flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # If admin is already logged in, show role selection
    is_admin = current_user.is_authenticated and current_user.role.name == 'admin'

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        real_name = request.form.get('real_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        # Admin can set any role, self-registration: teacher or student only
        if is_admin:
            role_id = request.form.get('role_id', type=int)
        else:
            role_id = request.form.get('role_id', type=int) or 3
            if role_id not in (2, 3):
                role_id = 3

        errors = []
        if not username or len(username) < 3:
            errors.append('用户名至少3个字符')
        if User.query.filter_by(username=username).first():
            errors.append('用户名已存在')
        if not password or len(password) < 6:
            errors.append('密码至少6个字符')
        if password != confirm:
            errors.append('两次密码不一致')
        if not real_name:
            errors.append('请输入真实姓名')
        if role_id not in (1, 2, 3):
            errors.append('请选择有效角色')

        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            user = User(username=username, real_name=real_name, email=email, phone=phone, role_id=role_id)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'注册成功，请登录', 'success')
            if is_admin:
                return redirect(url_for('admin.users'))
            return redirect(url_for('auth.login'))

    from app.models import Role
    roles = Role.query.all() if is_admin else []
    return render_template('auth/register.html', roles=roles, is_admin=is_admin)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.real_name = request.form.get('real_name', '').strip()
        current_user.email = request.form.get('email', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        db.session.commit()
        flash('个人信息已更新', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if not current_user.check_password(old_pw):
            flash('原密码错误', 'danger')
        elif len(new_pw) < 6:
            flash('新密码至少6个字符', 'danger')
        elif new_pw != confirm:
            flash('两次新密码不一致', 'danger')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('密码已修改', 'success')
            return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html')
