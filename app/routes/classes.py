import random
import string
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import (Class, ClassMember, User, Team, Course, Project,
                        TeamMember, Task, DailyReport, Announcement, TeamDocument)
from app.utils.decorators import role_required, log_activity

class_bp = Blueprint('class', __name__)


def _gen_invite_code():
    """生成 6 位字母数字邀请码"""
    chars = string.ascii_uppercase + string.digits
    # 去掉容易混淆的字符
    chars = ''.join(c for c in chars if c not in '0O1I')
    return ''.join(random.choices(chars, k=6))


# ---- 班级列表 ----
@class_bp.route('/')
@login_required
def list_classes():
    show_archived = request.args.get('archived') == '1'

    if current_user.role.name == 'admin':
        query = Class.query
    elif current_user.role.name == 'teacher':
        class_ids = db.session.query(ClassMember.class_id).filter_by(user_id=current_user.id).all()
        class_ids = [c[0] for c in class_ids]
        query = Class.query.filter(
            or_(Class.created_by == current_user.id, Class.id.in_(class_ids)))
    else:
        class_ids = db.session.query(ClassMember.class_id).filter_by(user_id=current_user.id).all()
        class_ids = [c[0] for c in class_ids]
        query = Class.query.filter(Class.id.in_(class_ids)) if class_ids else Class.query.filter(Class.id == -1)

    if not show_archived:
        query = query.filter_by(is_archived=False)

    classes = query.order_by(Class.created_at.desc()).all()
    return render_template('classes/list.html', classes=classes, show_archived=show_archived)


# ---- 创建班级 ----
@class_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def create_class():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        if not name:
            flash('请输入班级名称', 'danger')
            return render_template('classes/form.html')
        # 生成唯一邀请码
        for _ in range(10):
            code = _gen_invite_code()
            if not Class.query.filter_by(invite_code=code).first():
                break
        cls = Class(name=name, description=description, invite_code=code,
                    created_by=current_user.id)
        db.session.add(cls)
        db.session.flush()
        # 创建者自动加入为教师
        member = ClassMember(class_id=cls.id, user_id=current_user.id, role_in_class='teacher')
        db.session.add(member)
        db.session.commit()
        log_activity('create', 'class', 'Class', cls.id, {'name': name, 'invite_code': code})
        flash(f'班级「{name}」创建成功，邀请码：{code}', 'success')
        return redirect(url_for('class.class_detail', class_id=cls.id))
    return render_template('classes/form.html')


# ---- 班级详情 ----
@class_bp.route('/<int:class_id>')
@login_required
def class_detail(class_id):
    cls = db.session.get(Class, class_id)
    if not cls:
        flash('班级不存在', 'danger')
        return redirect(url_for('class.list_classes'))
    # 检查权限
    is_member = ClassMember.query.filter_by(class_id=class_id, user_id=current_user.id).first()
    if current_user.role.name not in ('admin', 'teacher') and not is_member:
        flash('你不在该班级中', 'danger')
        return redirect(url_for('class.list_classes'))
    # 归档班级学生不能访问
    if cls.is_archived and current_user.role.name == 'student':
        flash('该班级已归档，无法访问', 'danger')
        return redirect(url_for('class.list_classes'))

    members = ClassMember.query.filter_by(class_id=class_id).all()
    courses = Course.query.filter_by(class_id=class_id).order_by(Course.created_at.desc()).all()
    teams = Team.query.filter_by(class_id=class_id).order_by(Team.created_at.desc()).all()
    student_count = ClassMember.query.filter_by(class_id=class_id, role_in_class='student').count()
    teacher_count = ClassMember.query.filter_by(class_id=class_id, role_in_class='teacher').count()

    return render_template('classes/detail.html', cls=cls, members=members,
                           courses=courses, teams=teams,
                           student_count=student_count, teacher_count=teacher_count)


# ---- 加入班级 ----
@class_bp.route('/join', methods=['GET', 'POST'])
@login_required
def join_class():
    if request.method == 'POST':
        code = request.form.get('invite_code', '').strip().upper()
        if not code:
            flash('请输入邀请码', 'danger')
            return render_template('classes/join.html')
        cls = Class.query.filter_by(invite_code=code).first()
        if not cls:
            flash('邀请码无效', 'danger')
            return render_template('classes/join.html')
        if cls.is_archived:
            flash('该班级已归档', 'danger')
            return redirect(url_for('class.list_classes'))
        existing = ClassMember.query.filter_by(class_id=cls.id, user_id=current_user.id).first()
        if existing:
            flash('你已经在班级中', 'warning')
            return redirect(url_for('class.class_detail', class_id=cls.id))
        # 学生只能加入一个班级，如果已在其他班级则不允许
        if current_user.role.name == 'student':
            other_class = ClassMember.query.filter_by(user_id=current_user.id, role_in_class='student').first()
            if other_class:
                flash('你已加入其他班级，一个学生只能加入一个班级', 'danger')
                return redirect(url_for('class.list_classes'))
        role = 'student'
        if current_user.role.name in ('admin', 'teacher'):
            role = 'teacher'
        member = ClassMember(class_id=cls.id, user_id=current_user.id, role_in_class=role)
        db.session.add(member)
        db.session.commit()
        log_activity('join', 'class', 'Class', cls.id, {'user': current_user.real_name, 'role': role})
        flash(f'成功加入班级「{cls.name}」', 'success')
        return redirect(url_for('class.class_detail', class_id=cls.id))
    return render_template('classes/join.html')


# ---- 退出班级 ----
@class_bp.route('/<int:class_id>/leave', methods=['POST'])
@login_required
def leave_class(class_id):
    member = ClassMember.query.filter_by(class_id=class_id, user_id=current_user.id).first()
    if not member:
        flash('你不在此班级中', 'warning')
    elif member.role_in_class == 'teacher' and current_user.role.name != 'admin':
        flash('教师不能退出班级', 'danger')
    else:
        db.session.delete(member)
        db.session.commit()
        flash('已退出班级', 'success')
    return redirect(url_for('class.list_classes'))


# ---- 更换邀请码 ----
@class_bp.route('/<int:class_id>/new-code', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def new_invite_code(class_id):
    cls = db.session.get(Class, class_id)
    if not cls:
        flash('班级不存在', 'danger')
        return redirect(url_for('class.list_classes'))
    for _ in range(10):
        code = _gen_invite_code()
        if not Class.query.filter_by(invite_code=code).first():
            break
    cls.invite_code = code
    db.session.commit()
    flash(f'新邀请码：{code}', 'success')
    return redirect(url_for('class.class_detail', class_id=cls.id))


# ---- 移除成员 ----
@class_bp.route('/<int:class_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def remove_member(class_id, user_id):
    member = ClassMember.query.filter_by(class_id=class_id, user_id=user_id).first()
    if member:
        user = member.user
        db.session.delete(member)
        db.session.commit()
        flash(f'已移除 {user.real_name}', 'success')
    return redirect(url_for('class.class_detail', class_id=class_id))


# ---- 归档/取消归档 ----
@class_bp.route('/<int:class_id>/toggle-archive', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def toggle_archive(class_id):
    cls = db.session.get(Class, class_id)
    if cls:
        cls.is_archived = not cls.is_archived
        db.session.commit()
        flash(f'班级已{"归档" if cls.is_archived else "取消归档"}', 'success')
    return redirect(url_for('class.class_detail', class_id=class_id))


# ---- 编辑班级 ----
@class_bp.route('/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def edit_class(class_id):
    cls = db.session.get(Class, class_id)
    if not cls:
        flash('班级不存在', 'danger')
        return redirect(url_for('class.list_classes'))
    if request.method == 'POST':
        cls.name = request.form.get('name', '').strip()
        cls.description = request.form.get('description', '').strip()
        db.session.commit()
        log_activity('update', 'class', 'Class', cls.id, {'name': cls.name})
        flash('班级信息已更新', 'success')
        return redirect(url_for('class.class_detail', class_id=cls.id))
    return render_template('classes/form.html', cls=cls)


# ---- 删除班级 ----
@class_bp.route('/<int:class_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_class(class_id):
    cls = db.session.get(Class, class_id)
    if cls:
        try:
            # 清理关联数据
            from app.models import TeamDocument, Notification
            for team in Team.query.filter_by(class_id=class_id).all():
                TeamDocument.query.filter_by(team_id=team.id).delete()
                Task.query.filter_by(team_id=team.id).delete()
                DailyReport.query.filter_by(team_id=team.id).update({'team_id': None})
                TeamMember.query.filter_by(team_id=team.id).delete()
            Team.query.filter_by(class_id=class_id).delete()
            for course in Course.query.filter_by(class_id=class_id).all():
                Project.query.filter_by(course_id=course.id).delete()
            Course.query.filter_by(class_id=class_id).delete()
            Announcement.query.filter_by(class_id=class_id).update({'class_id': None})
            ClassMember.query.filter_by(class_id=class_id).delete()
            db.session.delete(cls)
            db.session.commit()
            flash('班级已删除', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'删除失败：班级下有关联数据', 'danger')
    return redirect(url_for('class.list_classes'))
