from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Task, Project, Team, Bug, User

task_bp = Blueprint('task', __name__)


@task_bp.route('/board')
@login_required
def board():
    project_id = request.args.get('project_id', type=int)
    team_id = request.args.get('team_id', type=int)
    assignee_id = request.args.get('assignee_id', type=int)

    query = Task.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if team_id:
        query = query.filter_by(team_id=team_id)
    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)

    tasks = query.order_by(Task.created_at.desc()).all()
    statuses = ['todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed']

    tasks_by_status = {s: [t for t in tasks if t.status == s] for s in statuses}
    projects = Project.query.all()
    teams = Team.query.all()
    users = User.query.filter(User.role.has(name='student')).all()

    return render_template('tasks/board.html',
                           tasks_by_status=tasks_by_status,
                           statuses=statuses,
                           projects=projects, teams=teams, users=users,
                           filter_project=project_id, filter_team=team_id, filter_assignee=assignee_id)


@task_bp.route('/list')
@login_required
def list_tasks():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    assignee_id = request.args.get('assignee_id', type=int)

    query = Task.query
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)

    tasks = query.order_by(Task.updated_at.desc()).paginate(page=page, per_page=15)
    return render_template('tasks/list.html', tasks=tasks, status_filter=status, priority_filter=priority, assignee_filter=assignee_id)


@task_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        task = Task(
            project_id=request.form.get('project_id', type=int),
            team_id=request.form.get('team_id', type=int) or None,
            title=request.form.get('title', '').strip(),
            description=request.form.get('description', ''),
            assignee_id=request.form.get('assignee_id', type=int) or None,
            priority=request.form.get('priority', 'medium'),
            status=request.form.get('status', 'todo'),
            start_date=request.form.get('start_date') or None,
            due_date=request.form.get('due_date') or None,
            estimated_hours=request.form.get('estimated_hours', type=float) or 0,
            related_bug_id=request.form.get('related_bug_id', type=int) or None
        )
        db.session.add(task)
        db.session.commit()
        flash('任务创建成功', 'success')
        return redirect(url_for('task.board'))
    projects = Project.query.all()
    teams = Team.query.all()
    users = User.query.filter(User.role.has(name='student')).all()
    bugs = Bug.query.filter(Bug.status.in_(['new', 'confirmed'])).all()
    return render_template('tasks/form.html', projects=projects, teams=teams, users=users, bugs=bugs)


@task_bp.route('/<int:task_id>')
@login_required
def task_detail(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.board'))
    return render_template('tasks/detail.html', task=task)


@task_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.board'))
    if request.method == 'POST':
        task.title = request.form.get('title', '').strip()
        task.description = request.form.get('description', '')
        task.assignee_id = request.form.get('assignee_id', type=int) or None
        task.team_id = request.form.get('team_id', type=int) or None
        task.priority = request.form.get('priority', 'medium')
        task.status = request.form.get('status', 'todo')
        task.start_date = request.form.get('start_date') or None
        task.due_date = request.form.get('due_date') or None
        task.estimated_hours = request.form.get('estimated_hours', type=float) or 0
        task.actual_hours = request.form.get('actual_hours', type=float) or 0
        task.completion_note = request.form.get('completion_note', '')
        task.related_bug_id = request.form.get('related_bug_id', type=int) or None
        db.session.commit()
        flash('任务已更新', 'success')
        return redirect(url_for('task.task_detail', task_id=task.id))
    projects = Project.query.all()
    teams = Team.query.all()
    users = User.query.filter(User.role.has(name='student')).all()
    bugs = Bug.query.all()
    return render_template('tasks/form.html', task=task, projects=projects, teams=teams, users=users, bugs=bugs)


@task_bp.route('/<int:task_id>/status', methods=['POST'])
@login_required
def update_status(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'not found'}), 404
    new_status = request.form.get('status') or request.json.get('status')
    allowed = ['todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed']
    if new_status in allowed:
        task.status = new_status
        db.session.commit()
        if request.is_json:
            return jsonify({'ok': True, 'status': new_status})
    flash('状态已更新', 'success')
    return redirect(url_for('task.board'))


@task_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task and current_user.role.name in ('admin', 'teacher'):
        db.session.delete(task)
        db.session.commit()
        flash('任务已删除', 'success')
    return redirect(url_for('task.board'))
