from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.extensions import db
from app.models import User, Role, LoginLog
from app.utils.decorators import role_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', type=int)

    query = User.query
    if search:
        query = query.filter(
            db.or_(User.username.contains(search), User.real_name.contains(search))
        )
    if role_filter:
        query = query.filter_by(role_id=role_filter)

    users_paginated = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15)
    roles = Role.query.all()
    return render_template('admin/users.html', users=users_paginated, roles=roles, search=search, role_filter=role_filter)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin.users'))
    if user.username == 'admin':
        flash('不能禁用超级管理员', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    user.login_fail_count = 0
    db.session.commit()
    flash(f'用户已{"启用" if user.is_active else "禁用"}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('admin')
def change_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin.users'))
    if user.username == 'admin':
        flash('不能修改超级管理员角色', 'danger')
        return redirect(url_for('admin.users'))
    new_role = request.form.get('role_id', type=int)
    if new_role in (1, 2, 3):
        user.role_id = new_role
        db.session.commit()
        flash('角色已更新', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在', 'danger')
    elif user.username == 'admin':
        flash('不能删除超级管理员', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('用户已删除', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/logs')
@login_required
@role_required('admin')
def logs():
    page = request.args.get('page', 1, type=int)
    logs = LoginLog.query.order_by(LoginLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/logs.html', logs=logs)
