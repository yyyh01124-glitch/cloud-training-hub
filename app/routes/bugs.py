from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models import Bug, User, ClassMember, Project, Team
from app.utils.decorators import log_activity, send_notification

bug_bp = Blueprint('bug', __name__)


@bug_bp.route('/')
@login_required
def list_bugs():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    severity = request.args.get('severity', '')
    query = Bug.query
    # 学生只看自己相关，教师只看自己班级
    if current_user.role.name == 'student':
        query = query.filter(db.or_(Bug.reporter_id == current_user.id, Bug.assignee_id == current_user.id))
    elif current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        student_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter(
            ClassMember.class_id.in_(class_ids), ClassMember.role_in_class == 'student').all()] if class_ids else []
        if student_ids:
            query = query.filter(db.or_(Bug.reporter_id.in_(student_ids), Bug.assignee_id.in_(student_ids)))
        else:
            query = query.filter(Bug.id == -1)
    if status:
        query = query.filter_by(status=status)
    if severity:
        query = query.filter_by(severity=severity)
    bugs = query.order_by(Bug.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('bugs/list.html', bugs=bugs, status_filter=status, severity_filter=severity)


@bug_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_bug():
    if request.method == 'POST':
        bug = Bug(
            project_id=request.form.get('project_id', type=int) or None,
            team_id=request.form.get('team_id', type=int) or None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', ''),
            repro_steps=request.form.get('repro_steps', ''),
            expected_result=request.form.get('expected_result', ''),
            actual_result=request.form.get('actual_result', ''),
            module=request.form.get('module', ''),
            severity=request.form.get('severity', 'normal'),
            estimated_hours=max(0, request.form.get('estimated_hours', type=float) or 0),
            actual_hours=max(0, request.form.get('actual_hours', type=float) or 0),
            reporter_id=current_user.id,
            assignee_id=request.form.get('assignee_id', type=int) or None
        )
        screenshot = request.files.get('screenshot')
        if screenshot and screenshot.filename:
            from app.utils.upload import save_upload
            bug.screenshot_url = save_upload(screenshot, 'bug_screenshots')
        db.session.add(bug)
        db.session.commit()
        log_activity('create', 'bug', 'Bug', bug.id, {'title': bug.title, 'severity': bug.severity})
        if bug.assignee_id:
            send_notification(bug.assignee_id, 'bug_assigned', f'Bug 指派：{bug.title}',
                              f'你被指派了一个Bug', url_for('bug.bug_detail', bug_id=bug.id))
        flash('Bug 已提交', 'success')
        return redirect(url_for('bug.list_bugs'))
    users = User.query.filter(User.is_active == True).all()
    projects = Project.query.order_by(Project.name).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('bugs/form.html', users=users, projects=projects, teams=teams)


@bug_bp.route('/<int:bug_id>')
@login_required
def bug_detail(bug_id):
    bug = db.session.get(Bug, bug_id)
    if not bug:
        flash('Bug 不存在', 'danger')
        return redirect(url_for('bug.list_bugs'))
    return render_template('bugs/detail.html', bug=bug)


@bug_bp.route('/<int:bug_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bug(bug_id):
    bug = db.session.get(Bug, bug_id)
    if not bug:
        flash('Bug 不存在', 'danger')
        return redirect(url_for('bug.list_bugs'))
    if request.method == 'POST':
        bug.project_id = request.form.get('project_id', type=int) or None
        bug.team_id = request.form.get('team_id', type=int) or None
        bug.title = request.form.get('title', '').strip()
        bug.description = request.form.get('description', '')
        bug.repro_steps = request.form.get('repro_steps', '')
        bug.expected_result = request.form.get('expected_result', '')
        bug.actual_result = request.form.get('actual_result', '')
        bug.module = request.form.get('module', '')
        bug.severity = request.form.get('severity', 'normal')
        bug.estimated_hours = max(0, request.form.get('estimated_hours', type=float) or 0)
        bug.actual_hours = max(0, request.form.get('actual_hours', type=float) or 0)
        bug.assignee_id = request.form.get('assignee_id', type=int) or None
        bug.status = request.form.get('status', 'new')
        bug.solution = request.form.get('solution', '')
        if request.form.get('status') == 'closed' and not bug.closed_at:
            bug.closed_at = datetime.utcnow()
        screenshot = request.files.get('screenshot')
        if screenshot and screenshot.filename:
            from app.utils.upload import save_upload
            bug.screenshot_url = save_upload(screenshot, 'bug_screenshots')
        db.session.commit()
        log_activity('update', 'bug', 'Bug', bug.id, {'title': bug.title, 'status': bug.status})
        flash('Bug 已更新', 'success')
        return redirect(url_for('bug.bug_detail', bug_id=bug.id))
    users = User.query.filter(User.is_active == True).all()
    projects = Project.query.order_by(Project.name).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('bugs/form.html', bug=bug, users=users, projects=projects, teams=teams)


@bug_bp.route('/<int:bug_id>/status', methods=['POST'])
@login_required
def update_status(bug_id):
    bug = db.session.get(Bug, bug_id)
    if not bug:
        flash('Bug 不存在', 'danger')
        return redirect(url_for('bug.list_bugs'))
    new_status = request.form.get('status')
    valid_transitions = {
        'new': ['confirmed', 'wontfix'],
        'confirmed': ['fixing', 'wontfix'],
        'fixing': ['fixed', 'wontfix'],
        'fixed': ['closed'],
        'closed': [],
        'wontfix': [],
    }
    if new_status in valid_transitions.get(bug.status, []):
        bug.status = new_status
        if new_status == 'closed':
            bug.closed_at = datetime.utcnow()
        db.session.commit()
        flash('状态已更新', 'success')
    else:
        flash('无效的状态转换', 'danger')
    return redirect(url_for('bug.bug_detail', bug_id=bug.id))


@bug_bp.route('/<int:bug_id>/delete', methods=['POST'])
@login_required
def delete_bug(bug_id):
    bug = db.session.get(Bug, bug_id)
    if bug and current_user.role.name in ('admin', 'teacher'):
        db.session.delete(bug)
        db.session.commit()
        flash('Bug 已删除', 'success')
    return redirect(url_for('bug.list_bugs'))
