from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Task, Project, Team, Bug, User, ClassMember, TeamMember
from app.utils.decorators import log_activity, send_notification, role_required

task_bp = Blueprint('task', __name__)


@task_bp.route('/board')
@login_required
def board():
    project_id = request.args.get('project_id', type=int)
    team_id = request.args.get('team_id', type=int)
    assignee_id = request.args.get('assignee_id', type=int)

    # 学生默认显示自己小组
    if current_user.role.name == 'student' and not team_id and not request.args.get('team_id'):
        my_team = TeamMember.query.filter_by(user_id=current_user.id).first()
        if my_team:
            team_id = my_team.team_id

    query = Task.query
    # 教师只看到自己班级的任务
    if current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        if class_ids:
            query = query.outerjoin(Team, Task.team_id == Team.id).filter(
                db.or_(Team.class_id.in_(class_ids), Task.team_id == None))
        else:
            query = query.filter(Task.id == -1)
    # 学生只看自己班级的任务
    if current_user.role.name == 'student':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='student').all()]
        if class_ids:
            query = query.outerjoin(Team, Task.team_id == Team.id).filter(
                db.or_(Team.class_id.in_(class_ids), Task.team_id == None))
        else:
            query = query.filter(Task.id == -1)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if team_id:
        query = query.filter(Task.team_id == team_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    tasks = query.order_by(Task.created_at.desc()).all()
    statuses = ['todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed']

    tasks_by_status = {s: [t for t in tasks if t.status == s] for s in statuses}
    projects = Project.query.all()
    teams = Team.query.all()
    users = User.query.filter(User.role.has(name='student')).all()

    # 学生的"我的小组"信息
    my_team = None
    if current_user.role.name == 'student':
        tm = TeamMember.query.filter_by(user_id=current_user.id).first()
        if tm:
            my_team = tm.team

    return render_template('tasks/board.html',
                           tasks_by_status=tasks_by_status,
                           statuses=statuses,
                           projects=projects, teams=teams, users=users,
                           filter_project=project_id, filter_team=team_id, filter_assignee=assignee_id,
                           my_team=my_team)


@task_bp.route('/list')
@login_required
def list_tasks():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    assignee_id = request.args.get('assignee_id', type=int)

    query = Task.query
    # 教师只看到自己班级的任务
    if current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        if class_ids:
            query = query.outerjoin(Team, Task.team_id == Team.id).filter(
                db.or_(Team.class_id.in_(class_ids), Task.team_id == None))
        else:
            query = query.filter(Task.id == -1)
    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    tasks = query.order_by(Task.updated_at.desc()).paginate(page=page, per_page=15)
    return render_template('tasks/list.html', tasks=tasks, status_filter=status, priority_filter=priority, assignee_filter=assignee_id)


@task_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
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
        screenshot = request.files.get('screenshot')
        if screenshot and screenshot.filename:
            from app.utils.upload import save_upload
            task.screenshot_url = save_upload(screenshot, 'screenshots')
        db.session.add(task)
        db.session.commit()
        log_activity('create', 'task', 'Task', task.id, {'title': task.title})
        if task.assignee_id:
            send_notification(task.assignee_id, 'task_assigned', f'新任务：{task.title}',
                              f'你被分配了一个新任务', url_for('task.task_detail', task_id=task.id))
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
@role_required('admin', 'teacher')
def edit_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        flash('任务不存在', 'danger')
        return redirect(url_for('task.board'))
    if request.method == 'POST':
        new_status = request.form.get('status', 'todo')
        original_assignee = task.assignee_id
        # 状态流转校验：进行中→待测试 至少需要一个交付物
        deliverables = list(task.deliverables or [])
        if task.status == 'in_progress' and new_status == 'to_test' and not deliverables:
            flash('请先上传至少一个交付物（文件或链接），才能将任务提交测试', 'danger')
            projects = Project.query.all()
            teams = Team.query.all()
            users = User.query.filter(User.role.has(name='student')).all()
            bugs = Bug.query.all()
            return render_template('tasks/form.html', task=task, projects=projects, teams=teams, users=users, bugs=bugs)

        task.title = request.form.get('title', '').strip()
        task.description = request.form.get('description', '')
        task.assignee_id = request.form.get('assignee_id', type=int) or None
        task.team_id = request.form.get('team_id', type=int) or None
        task.priority = request.form.get('priority', 'medium')
        task.status = new_status
        task.start_date = request.form.get('start_date') or None
        task.due_date = request.form.get('due_date') or None
        task.estimated_hours = request.form.get('estimated_hours', type=float) or 0
        task.actual_hours = request.form.get('actual_hours', type=float) or 0
        task.completion_note = request.form.get('completion_note', '')
        task.related_bug_id = request.form.get('related_bug_id', type=int) or None

        screenshot = request.files.get('screenshot')
        if screenshot and screenshot.filename:
            from app.utils.upload import save_upload
            task.screenshot_url = save_upload(screenshot, 'screenshots')

        # 处理交付物文件上传
        from datetime import datetime as dt
        deliverable_files = request.files.getlist('deliverable_files')
        for f in deliverable_files:
            if f and f.filename:
                from app.utils.upload import save_upload
                path = save_upload(f, 'deliverables')
                deliverables.append({
                    'type': 'file', 'url': '/' + path, 'name': f.filename,
                    'uploaded_at': dt.utcnow().strftime('%Y-%m-%d %H:%M')
                })

        # 处理交付物链接（禁止 javascript: 等危险协议）
        link_url = request.form.get('deliverable_link', '').strip()
        if link_url and link_url.lower().startswith(('http://', 'https://', '/')):
            link_name = request.form.get('deliverable_link_name', '').strip() or link_url
            deliverables.append({
                'type': 'link', 'url': link_url, 'name': link_name,
                'uploaded_at': dt.utcnow().strftime('%Y-%m-%d %H:%M')
            })

        task.deliverables = deliverables if deliverables else None
        db.session.commit()
        log_activity('update', 'task', 'Task', task.id, {'title': task.title, 'status': task.status})
        # 如果负责人变更了，通知新负责人
        if task.assignee_id and task.assignee_id != original_assignee:
            send_notification(task.assignee_id, 'task_assigned', f'任务分配：{task.title}',
                              f'你被分配了任务「{task.title}」', url_for('task.task_detail', task_id=task.id))
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
    # 学生只能拖拽自己的任务
    if current_user.role.name == 'student' and task.assignee_id != current_user.id:
        if request.is_json:
            return jsonify({'ok': False, 'error': '无权限'}), 403
        flash('无权限', 'danger')
        return redirect(url_for('task.board'))
    new_status = request.form.get('status') or (request.get_json(silent=True) or {}).get('status')
    allowed = ['todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed']
    if new_status in allowed:
        task.status = new_status
        db.session.commit()
        if request.is_json:
            return jsonify({'ok': True, 'status': new_status})
    flash('状态已更新', 'success')
    return redirect(url_for('task.board'))


@task_bp.route('/overview')
@login_required
def teacher_overview():
    if current_user.role.name not in ('admin', 'teacher'):
        return redirect(url_for('task.board'))
    from sqlalchemy import func as safunc
    projects = Project.query.all()
    stats = []
    for p in projects:
        tasks_by_status = {}
        for s in ['todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed']:
            tasks_by_status[s] = Task.query.filter_by(project_id=p.id, status=s).count()
        stats.append({
            'project_name': p.name,
            'project_id': p.id,
            'status_counts': tasks_by_status,
            'total': sum(tasks_by_status.values())
        })
    return render_template('tasks/overview.html', stats=stats)


@task_bp.route('/<int:task_id>/deliverable/<int:idx>/remove', methods=['POST'])
@login_required
@role_required('admin', 'teacher')
def remove_deliverable(task_id, idx):
    task = db.session.get(Task, task_id)
    if task and task.deliverables and 0 <= idx < len(task.deliverables):
        dl = list(task.deliverables)
        dl.pop(idx)
        task.deliverables = dl if dl else None
        db.session.commit()
        flash('交付物已移除', 'success')
    return redirect(url_for('task.task_detail', task_id=task_id))


@task_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task and current_user.role.name in ('admin', 'teacher'):
        db.session.delete(task)
        db.session.commit()
        flash('任务已删除', 'success')
    return redirect(url_for('task.board'))
