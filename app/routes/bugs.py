from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.extensions import db
from app.models import Bug, User

bug_bp = Blueprint('bug', __name__)


@bug_bp.route('/')
@login_required
def list_bugs():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    severity = request.args.get('severity', '')
    query = Bug.query
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
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', ''),
            repro_steps=request.form.get('repro_steps', ''),
            expected_result=request.form.get('expected_result', ''),
            actual_result=request.form.get('actual_result', ''),
            module=request.form.get('module', ''),
            severity=request.form.get('severity', 'normal'),
            reporter_id=current_user.id,
            assignee_id=request.form.get('assignee_id', type=int) or None
        )
        db.session.add(bug)
        db.session.commit()
        flash('Bug 已提交', 'success')
        return redirect(url_for('bug.list_bugs'))
    users = User.query.filter(User.is_active == True).all()
    return render_template('bugs/form.html', users=users)


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
        bug.title = request.form.get('title', '').strip()
        bug.description = request.form.get('description', '')
        bug.repro_steps = request.form.get('repro_steps', '')
        bug.expected_result = request.form.get('expected_result', '')
        bug.actual_result = request.form.get('actual_result', '')
        bug.module = request.form.get('module', '')
        bug.severity = request.form.get('severity', 'normal')
        bug.assignee_id = request.form.get('assignee_id', type=int) or None
        bug.status = request.form.get('status', 'new')
        bug.solution = request.form.get('solution', '')
        if request.form.get('status') == 'closed' and not bug.closed_at:
            bug.closed_at = datetime.utcnow()
        db.session.commit()
        flash('Bug 已更新', 'success')
        return redirect(url_for('bug.bug_detail', bug_id=bug.id))
    users = User.query.filter(User.is_active == True).all()
    return render_template('bugs/form.html', bug=bug, users=users)


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
