from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Team, TeamMember, TeamDocument, Project, User, ClassMember, Course
from app.utils.decorators import log_activity

team_bp = Blueprint('team', __name__)


@team_bp.route('/')
@login_required
def list_teams():
    page = request.args.get('page', 1, type=int)
    project_id = request.args.get('project_id', type=int)
    tab = request.args.get('tab', 'my' if current_user.role.name == 'student' else 'all')
    query = Team.query
    # 学生只看自己班级的；教师只看自己班级的
    if current_user.role.name == 'student':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='student').all()]
        query = query.filter(Team.class_id.in_(class_ids)) if class_ids else query.filter(Team.id == -1)
        if tab == 'my':
            my_team_id = db.session.query(TeamMember.team_id).filter_by(user_id=current_user.id).scalar()
            query = query.filter(Team.id == my_team_id) if my_team_id else query.filter(Team.id == -1)
    elif current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        query = query.filter(Team.class_id.in_(class_ids)) if class_ids else query.filter(Team.id == -1)
    if project_id:
        query = query.filter_by(project_id=project_id)
    teams = query.order_by(Team.created_at.desc()).paginate(page=page, per_page=12)
    # 项目筛选列表
    if current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        projects = Project.query.join(Course).filter(Course.class_id.in_(class_ids)).all() if class_ids else []
    else:
        projects = Project.query.all()
    return render_template('teams/list.html', teams=teams, projects=projects, project_filter=project_id, tab=tab)


@team_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_team():
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        # 学生加入小组时检查：不能在班级内重复加入
        if current_user.role.name == 'student':
            project = db.session.get(Project, project_id)
            if project:
                course = db.session.get(Course, project.course_id)
                if course and course.class_id:
                    class_member = TeamMember.query.join(Team).filter(
                        Team.class_id == course.class_id,
                        TeamMember.user_id == current_user.id
                    ).first()
                    if class_member:
                        flash('你已在该班级的其他小组中', 'danger')
                        return redirect(url_for('team.list_teams'))

        # 从项目的课程获取班级ID
        class_id = None
        if project:
            course = db.session.get(Course, project.course_id)
            if course:
                class_id = course.class_id

        team = Team(
            project_id=project_id,
            class_id=class_id,
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', '')
        )
        db.session.add(team)
        db.session.flush()
        member = TeamMember(team_id=team.id, user_id=current_user.id, role_in_team='leader')
        team.leader_id = current_user.id
        db.session.add(member)
        db.session.commit()
        log_activity('create', 'team', 'Team', team.id, {'name': team.name})
        flash('小组创建成功', 'success')
        return redirect(url_for('team.team_detail', team_id=team.id))
    # 按班级过滤项目
    class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
        user_id=current_user.id).all()]
    if class_ids:
        projects = Project.query.join(Course).filter(Course.class_id.in_(class_ids)).all()
    else:
        projects = Project.query.all()
    return render_template('teams/form.html', projects=projects)


@team_bp.route('/<int:team_id>')
@login_required
def team_detail(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    # 任务完成率
    from app.models import Task, DailyReport
    tasks_total = Task.query.filter_by(team_id=team_id).count()
    tasks_done = Task.query.filter_by(team_id=team_id, status='done').count()
    tasks_delayed = Task.query.filter_by(team_id=team_id, status='delayed').count()
    task_rate = round(tasks_done / tasks_total * 100) if tasks_total > 0 else 0
    # 日报提交情况
    from datetime import date
    today = date.today()
    member_ids = [m.user_id for m in team.members.all()]
    reports_today = DailyReport.query.filter(
        DailyReport.user_id.in_(member_ids),
        DailyReport.report_date == today
    ).count() if member_ids else 0
    report_rate = round(reports_today / len(member_ids) * 100) if member_ids else 0
    return render_template('teams/detail.html', team=team,
                           tasks_total=tasks_total, tasks_done=tasks_done,
                           tasks_delayed=tasks_delayed, task_rate=task_rate,
                           reports_today=reports_today, report_rate=report_rate,
                           member_count=len(member_ids))


@team_bp.route('/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    # 只有组长或教师/管理员可以编辑
    if current_user.role.name == 'student' and team.leader_id != current_user.id:
        flash('只有组长可以编辑小组信息', 'danger')
        return redirect(url_for('team.team_detail', team_id=team.id))
    if request.method == 'POST':
        team.name = request.form.get('name', '').strip()
        team.description = request.form.get('description', '')
        team.deploy_url = request.form.get('deploy_url', '')
        team.doc_url = request.form.get('doc_url', '')
        db.session.commit()
        flash('小组信息已更新', 'success')
        return redirect(url_for('team.team_detail', team_id=team.id))
    return render_template('teams/form.html', team=team)


@team_bp.route('/<int:team_id>/join', methods=['POST'])
@login_required
def join_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    # 检查是否已在同一班级的其他小组中
    existing = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    if existing:
        flash('你已在此小组中', 'warning')
        return redirect(url_for('team.team_detail', team_id=team_id))
    if team.class_id:
        class_member = TeamMember.query.join(Team).filter(
            Team.class_id == team.class_id,
            TeamMember.user_id == current_user.id
        ).first()
        if class_member:
            flash('你已在该班级的其他小组中，一个学生只能加入一个小组', 'danger')
            return redirect(url_for('team.team_detail', team_id=team_id))
    member = TeamMember(team_id=team_id, user_id=current_user.id, role_in_team='member')
    db.session.add(member)
    db.session.commit()
    log_activity('join', 'team', 'Team', team_id, {'user': current_user.real_name})
    flash('成功加入小组', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/leave', methods=['POST'])
@login_required
def leave_team(team_id):
    member = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    if not member:
        flash('你不在此小组中', 'warning')
        return redirect(url_for('team.team_detail', team_id=team_id))
    if member.role_in_team == 'leader':
        flash('组长不能直接退出，请先转让组长', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    # 将退出的学生的任务负责人设为None
    from app.models import Task
    Task.query.filter_by(team_id=team_id, assignee_id=current_user.id).update({'assignee_id': None})
    db.session.delete(member)
    db.session.commit()
    flash('已退出小组，你负责的任务已取消分配', 'success')
    return redirect(url_for('team.list_teams'))


@team_bp.route('/<int:team_id>/members/add', methods=['POST'])
@login_required
def add_member(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    user_id = request.form.get('user_id', type=int)
    role_name = request.form.get('role_in_team', 'member')
    existing = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
    if existing:
        flash('该用户已在小组中', 'warning')
        return redirect(url_for('team.team_detail', team_id=team_id))
    member = TeamMember(team_id=team_id, user_id=user_id, role_in_team=role_name)
    if role_name == 'leader':
        team.leader_id = user_id
    db.session.add(member)
    db.session.commit()
    flash('成员已添加', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_member(team_id, user_id):
    member = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
    if member:
        if member.role_in_team == 'leader':
            flash('不能直接移除组长', 'danger')
            return redirect(url_for('team.team_detail', team_id=team_id))
        # 清理该成员在小组中的任务分配
        from app.models import Task
        Task.query.filter_by(team_id=team_id, assignee_id=user_id).update({'assignee_id': None})
        db.session.delete(member)
        db.session.commit()
        flash('成员已移除，其任务已取消分配', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/members/<int:user_id>/role', methods=['POST'])
@login_required
def change_member_role(team_id, user_id):
    member = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not member:
        flash('成员不存在', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    # 收集所有选中的角色
    team = db.session.get(Team, team_id)
    valid_roles = ['leader', 'backend', 'frontend', 'database', 'devops', 'member']
    selected = []
    for role in valid_roles:
        if request.form.get(f'role_{role}') == role:
            selected.append(role)
    if not selected:
        selected = ['member']
    new_roles = ','.join(selected)
    # 处理组长变更
    if 'leader' in selected and member.role_in_team and 'leader' not in (member.role_in_team or '').split(','):
        # 新组长：取消旧组长
        old_leader = TeamMember.query.filter(
            TeamMember.team_id == team_id,
            TeamMember.role_in_team.contains('leader')
        ).first()
        if old_leader:
            old_roles = [r for r in (old_leader.role_in_team or '').split(',') if r.strip() != 'leader']
            old_leader.role_in_team = ','.join(old_roles) if old_roles else 'member'
        team.leader_id = user_id
    member.role_in_team = new_roles
    db.session.commit()
    flash('角色已更新', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


# ---- 文档管理 ----

DOC_CATEGORIES = {
    'requirement': '需求说明书',
    'design': '系统设计文档',
    'database': '数据库设计文档',
    'test_report': '测试报告',
    'deploy_doc': '部署文档',
    'personal_summary': '个人总结',
    'ppt': '答辩PPT',
    'other': '其他'
}


@team_bp.route('/<int:team_id>/documents/upload', methods=['POST'])
@login_required
def upload_document(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    file = request.files.get('doc_file')
    if not file or not file.filename:
        flash('请选择文件', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    from app.utils.upload import save_upload
    path = save_upload(file, 'team_docs')
    if not path:
        flash('不支持的文件格式', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    doc = TeamDocument(
        team_id=team_id,
        name=request.form.get('doc_name', '').strip() or file.filename,
        doc_category=request.form.get('doc_category', 'other'),
        file_url='/' + path,
        uploaded_by=current_user.id
    )
    db.session.add(doc)
    db.session.commit()
    flash('文档已上传', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(team_id, doc_id):
    doc = db.session.get(TeamDocument, doc_id)
    if doc and doc.team_id == team_id:
        db.session.delete(doc)
        db.session.commit()
        flash('文档已删除', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/documents/download-all')
@login_required
def download_all_docs(team_id):
    if current_user.role.name not in ('admin', 'teacher'):
        flash('无权限', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    import zipfile
    from io import BytesIO
    from flask import send_file
    import os
    docs = TeamDocument.query.filter_by(team_id=team_id).all()
    if not docs:
        flash('该小组没有文档', 'warning')
        return redirect(url_for('team.team_detail', team_id=team_id))
    buf = BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), doc.file_url.lstrip('/'))
            if os.path.exists(filepath):
                zf.write(filepath, f'{doc.doc_category}/{doc.name}')
    buf.seek(0)
    team = db.session.get(Team, team_id)
    return send_file(buf, download_name=f'{team.name}_文档_{__import__("datetime").date.today()}.zip',
                     mimetype='application/zip', as_attachment=True)


@team_bp.route('/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    team = db.session.get(Team, team_id)
    if team and current_user.role.name in ('admin', 'teacher'):
        from app.models import Task, DailyReport
        Task.query.filter_by(team_id=team_id).update({'team_id': None})
        DailyReport.query.filter_by(team_id=team_id).update({'team_id': None})
        db.session.delete(team)
        db.session.commit()
        flash('小组已删除，关联任务已解除', 'success')
    return redirect(url_for('team.list_teams'))
