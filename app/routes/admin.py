from datetime import date, datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required

from app.extensions import db
from app.models import (User, Role, LoginLog, Task, DailyReport, Bug, Announcement,
                        SystemLog, TeamMember, ClassMember, AiRecord, Score, Team,
                        Class, Notification, TeamDocument, CrawlerConfig, Course, Project)
from app.utils.decorators import role_required, log_activity

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
    log_activity('toggle_active', 'admin', 'User', user.id, {'is_active': user.is_active, 'username': user.username})
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
        log_activity('change_role', 'admin', 'User', user.id, {'new_role': new_role, 'username': user.username})
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
        try:
            # 清理关联数据
            Notification.query.filter_by(user_id=user_id).delete()
            LoginLog.query.filter_by(user_id=user_id).delete()
            SystemLog.query.filter_by(user_id=user_id).delete()
            AiRecord.query.filter_by(user_id=user_id).delete()
            DailyReport.query.filter_by(user_id=user_id).delete()
            Task.query.filter_by(assignee_id=user_id).update({'assignee_id': None})
            Bug.query.filter_by(reporter_id=user_id).update({'reporter_id': None})
            Bug.query.filter_by(assignee_id=user_id).update({'assignee_id': None})
            TeamMember.query.filter_by(user_id=user_id).delete()
            TeamDocument.query.filter_by(uploaded_by=user_id).update({'uploaded_by': None})
            Team.query.filter_by(leader_id=user_id).update({'leader_id': None})
            Score.query.filter_by(student_id=user_id).delete()
            Score.query.filter_by(scored_by=user_id).delete()
            ClassMember.query.filter_by(user_id=user_id).delete()
            Class.query.filter_by(created_by=user_id).update({'created_by': None})
            Course.query.filter_by(teacher_id=user_id).update({'teacher_id': None})
            Project.query.filter_by(leader_id=user_id).update({'leader_id': None})
            Announcement.query.filter_by(publisher_id=user_id).delete()
            CrawlerConfig.query.filter_by(created_by=user_id).update({'created_by': None})
            db.session.flush()
            db.session.delete(user)
            db.session.commit()
            log_activity('delete', 'admin', 'User', user.id, {'username': user.username})
            flash('用户已删除', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'删除失败：该用户有关联数据无法删除', 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/import-students', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def import_students():
    """批量导入学生（Excel）"""
    if request.method == 'POST':
        file = request.files.get('file')
        class_id = request.form.get('class_id', type=int)
        if not file or not file.filename:
            flash('请选择文件', 'danger')
            return render_template('admin/import_students.html',
                                   classes=Class.query.filter_by(is_archived=False).all())

        import pandas as pd
        from io import BytesIO
        df = pd.read_excel(BytesIO(file.read()))
        required_cols = ['用户名', '姓名']
        for col in required_cols:
            if col not in df.columns:
                flash(f'缺少列：{col}，模板需包含：用户名、姓名、邮箱、手机号', 'danger')
                return render_template('admin/import_students.html',
                                       classes=Class.query.filter_by(is_archived=False).all())

        created = 0
        skipped = 0
        for _, row in df.iterrows():
            username = str(row['用户名']).strip()
            if not username:
                continue
            if User.query.filter_by(username=username).first():
                skipped += 1
                continue
            user = User(
                username=username,
                real_name=str(row.get('姓名', username)).strip(),
                email=str(row.get('邮箱', '')).strip(),
                phone=str(row.get('手机号', '')).strip(),
                role_id=3
            )
            user.set_password('123456')
            db.session.add(user)
            db.session.flush()
            # Add to class
            if class_id:
                db.session.add(ClassMember(class_id=class_id, user_id=user.id, role_in_class='student'))
            created += 1

        db.session.commit()
        flash(f'成功导入 {created} 名学生，跳过 {skipped} 个（用户名已存在）', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/import_students.html',
                           classes=Class.query.filter_by(is_archived=False).all())


@admin_bp.route('/export/<report_type>')
@login_required
@role_required('admin', 'teacher')
def export_data(report_type):
    import pandas as pd
    from io import BytesIO
    from flask import send_file

    if report_type == 'tasks':
        data = [{'标题': t.title, '项目': t.project.name if t.project else '', '负责人': t.assignee.real_name if t.assignee else '',
                 '状态': t.status, '优先级': t.priority, '截止': str(t.due_date or '')}
                for t in Task.query.all()]
    elif report_type == 'reports':
        data = [{'学生': r.user.real_name, '日期': str(r.report_date), '内容': r.completed_content or '',
                 '自评': r.self_score, '点评': r.teacher_comment or ''}
                for r in DailyReport.query.limit(200).all()]
    elif report_type == 'bugs':
        data = [{'标题': b.title, '严重程度': b.severity, '状态': b.status, '模块': b.module,
                 '提出人': b.reporter.real_name if b.reporter else '', '负责人': b.assignee.real_name if b.assignee else ''}
                for b in Bug.query.all()]
    elif report_type == 'users':
        data = [{'用户名': u.username, '姓名': u.real_name, '角色': u.role.display_name,
                 '状态': '启用' if u.is_active else '禁用', '邮箱': u.email, '手机': u.phone}
                for u in User.query.all()]
    else:
        flash('不支持的导出类型', 'danger')
        return redirect(url_for('admin.users'))

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=report_type, index=False)
    output.seek(0)
    return send_file(output, download_name=f'{report_type}_{date.today()}.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@admin_bp.route('/student/<int:user_id>')
@login_required
@role_required('admin', 'teacher')
def student_profile(user_id):
    """学生画像 - 聚合展示学生所有数据"""
    from datetime import date, datetime, timedelta
    student = db.session.get(User, user_id)
    if not student or student.role.name != 'student':
        flash('学生不存在', 'danger')
        return redirect(url_for('admin.users'))

    my_tasks_total = Task.query.filter_by(assignee_id=user_id).count()
    my_tasks_done = Task.query.filter_by(assignee_id=user_id, status='done').count()
    my_tasks_delayed = Task.query.filter_by(assignee_id=user_id, status='delayed').count()
    my_tasks_todo = Task.query.filter_by(assignee_id=user_id, status='todo').count()
    my_tasks_in_progress = Task.query.filter_by(assignee_id=user_id, status='in_progress').count()
    completion_rate = round(my_tasks_done / my_tasks_total * 100) if my_tasks_total > 0 else 0

    my_reports = DailyReport.query.filter_by(user_id=user_id).order_by(DailyReport.report_date.desc()).limit(10).all()
    report_count = DailyReport.query.filter_by(user_id=user_id).count()

    my_bugs_reported = Bug.query.filter_by(reporter_id=user_id).all()
    my_bugs_assigned = Bug.query.filter_by(assignee_id=user_id).all()
    bugs_fixed = Bug.query.filter_by(assignee_id=user_id, status='fixed').count()

    ai_count = AiRecord.query.filter_by(user_id=user_id).count()

    scores = Score.query.filter_by(student_id=user_id).order_by(Score.created_at.desc()).all()
    avg_score = round(sum(s.score for s in scores) / len(scores), 1) if scores else 0

    # Recent activity timeline
    activities = []
    for r in my_reports[:5]:
        activities.append({'type': 'report', 'desc': f'提交了日报', 'time': r.submitted_at or r.created_at})
    for t in Task.query.filter_by(assignee_id=user_id, status='done').order_by(Task.updated_at.desc()).limit(5):
        activities.append({'type': 'task_done', 'desc': f'完成了任务「{t.title}」', 'time': t.updated_at})
    for b in my_bugs_reported[:3]:
        activities.append({'type': 'bug', 'desc': f'提交了Bug「{b.title}」', 'time': b.created_at})
    activities.sort(key=lambda x: x['time'] if x['time'] else datetime(2000, 1, 1), reverse=True)
    activities = activities[:15]

    # Team info
    membership = TeamMember.query.filter_by(user_id=user_id).first()
    team_info = None
    if membership:
        team = membership.team
        team_tasks_total = Task.query.filter_by(team_id=team.id).count()
        team_tasks_done = Task.query.filter_by(team_id=team.id, status='done').count()
        team_info = {
            'name': team.name,
            'project': team.project.name if team.project else '',
            'role': membership.role_in_team,
            'task_rate': round(team_tasks_done / team_tasks_total * 100) if team_tasks_total > 0 else 0
        }

    # Class info
    cm = ClassMember.query.filter_by(user_id=user_id, role_in_class='student').first()
    class_info = cm.class_ if cm else None

    return render_template('admin/student_profile.html',
                           student=student, class_info=class_info,
                           my_tasks_total=my_tasks_total, my_tasks_done=my_tasks_done,
                           my_tasks_todo=my_tasks_todo, my_tasks_in_progress=my_tasks_in_progress,
                           my_tasks_delayed=my_tasks_delayed, completion_rate=completion_rate,
                           my_reports=my_reports, report_count=report_count,
                           bugs_reported_count=len(my_bugs_reported),
                           bugs_assigned_count=len(my_bugs_assigned),
                           bugs_fixed=bugs_fixed, ai_count=ai_count,
                           scores=scores, avg_score=avg_score,
                           activities=activities, team_info=team_info)


@admin_bp.route('/logs')
@login_required
@role_required('admin')
def logs():
    page = request.args.get('page', 1, type=int)
    tab = request.args.get('tab', 'login')
    login_logs = LoginLog.query.order_by(LoginLog.created_at.desc()).paginate(page=page, per_page=20)
    sys_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/logs.html', login_logs=login_logs, sys_logs=sys_logs, tab=tab)
