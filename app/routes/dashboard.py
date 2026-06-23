from datetime import date, timedelta, datetime as dt
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import (Project, Team, TeamMember, Task, User, Bug,
                        DailyReport, AiRecord, Announcement, Class, ClassMember,
                        SystemLog, LoginLog)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()

    # Get user's classes
    class_ids = [c[0] for c in db.session.query(ClassMember.class_id).filter_by(user_id=current_user.id).all()]
    user_classes = Class.query.filter(Class.id.in_(class_ids)).all() if class_ids else []

    if current_user.role.name == 'student':
        return student_dashboard(today, user_classes)

    if current_user.role.name == 'admin':
        return admin_dashboard(today)

    # For teacher: allow class switching
    selected_class_id = request.args.get('class_id', type=int)
    selected_class = None
    if selected_class_id and selected_class_id in [c.id for c in user_classes]:
        selected_class = db.session.get(Class, selected_class_id)
    elif user_classes:
        selected_class = user_classes[0]

    return teacher_dashboard(today, user_classes, selected_class)


def teacher_dashboard(today, user_classes, selected_class):
    # --- Base queries (class-scoped if selected) ---
    def scope(query, model):
        if selected_class and hasattr(model, 'class_id'):
            return query.filter(model.class_id == selected_class.id)
        return query

    # --- 预警数据 ---
    students_active = User.query.filter(User.role.has(name='student'), User.is_active == True)
    # Scope to class students
    if selected_class:
        cids = [m[0] for m in db.session.query(ClassMember.user_id).filter_by(
            class_id=selected_class.id, role_in_class='student').all()]
        students_active = students_active.filter(User.id.in_(cids)) if cids else students_active.filter(User.id == -1)

    students_list = students_active.all()
    missing_today = []
    for s in students_list:
        r = DailyReport.query.filter_by(user_id=s.id, report_date=today).first()
        if not r:
            tm = s.team_memberships.first()
            missing_today.append({
                'name': s.real_name,
                'team': tm.team.name if tm and tm.team else '未加入小组'
            })

    delayed_tasks = scope(Task.query, Task).filter(Task.status == 'delayed').count()
    unreviewed_reports = scope(DailyReport.query, DailyReport).filter(
        or_(DailyReport.teacher_comment == None, DailyReport.teacher_comment == '')
    ).count()

    # --- 待处理 ---
    pending_reviews = scope(DailyReport.query, DailyReport).filter(
        or_(DailyReport.teacher_comment == None, DailyReport.teacher_comment == '')
    ).order_by(DailyReport.report_date.desc()).limit(8).all()

    # --- 全局统计 ---
    teams = scope(Team.query, Team).all() if selected_class else Team.query.all()
    projects = scope(Project.query, Project).all() if selected_class else Project.query.all()
    students_count = len(students_list)
    tasks_total = scope(Task.query, Task).count()
    tasks_by_status = {
        'todo': scope(Task.query, Task).filter_by(status='todo').count(),
        'in_progress': scope(Task.query, Task).filter_by(status='in_progress').count(),
        'to_test': scope(Task.query, Task).filter_by(status='to_test').count(),
        'done': scope(Task.query, Task).filter_by(status='done').count(),
        'delayed': delayed_tasks,
    }
    bugs_total = scope(Bug.query, Bug).count() if selected_class else Bug.query.count()
    bugs_open = scope(Bug.query, Bug).filter(Bug.status.in_(['new', 'confirmed', 'fixing'])).count() if selected_class else Bug.query.filter(Bug.status.in_(['new', 'confirmed', 'fixing'])).count()
    reports_today = scope(DailyReport.query, DailyReport).filter_by(report_date=today).count()
    ai_count = scope(AiRecord.query, AiRecord).count() if selected_class else AiRecord.query.count()
    # 项目部署成功率（有deploy_url的team占总team的比例）
    teams_with_deploy = scope(Team.query, Team).filter(Team.deploy_url != '', Team.deploy_url != None).count()
    teams_total_count = scope(Team.query, Team).count()
    deploy_rate = round(teams_with_deploy / teams_total_count * 100) if teams_total_count > 0 else 0

    # --- 任务状态饼图 ---
    task_status_data = [
        {'name': '待开始', 'value': tasks_by_status['todo']},
        {'name': '进行中', 'value': tasks_by_status['in_progress']},
        {'name': '待测试', 'value': tasks_by_status['to_test']},
        {'name': '已完成', 'value': tasks_by_status['done']},
        {'name': '已延期', 'value': tasks_by_status['delayed']},
    ]

    # --- 小组进度排名 ---
    team_ranking = []
    for t in teams:
        done = Task.query.filter_by(team_id=t.id, status='done').count()
        total_t = Task.query.filter_by(team_id=t.id).count()
        rate = round(done / total_t * 100) if total_t > 0 else 0
        delayed = Task.query.filter_by(team_id=t.id, status='delayed').count()
        members = TeamMember.query.filter_by(team_id=t.id).count()
        team_ranking.append({
            'name': t.name, 'done': done, 'total': total_t,
            'rate': rate, 'delayed': delayed, 'members': members
        })
    team_ranking.sort(key=lambda x: x['rate'], reverse=True)

    # --- 日报提交趋势 ---
    report_dates = []
    report_counts = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        report_dates.append(d.strftime('%m-%d'))
        q = DailyReport.query.filter_by(report_date=d)
        if selected_class:
            q = scope(q, DailyReport)
        report_counts.append(q.count())

    # --- 班级对比数据（教多个班时） ---
    class_comparison = []
    if len(user_classes) > 1:
        for cls in user_classes:
            cids = [m[0] for m in db.session.query(ClassMember.user_id).filter_by(
                class_id=cls.id, role_in_class='student').all()]
            total_t = Task.query.filter(Task.team.has(class_id=cls.id)).count()
            done_t = Task.query.filter(Task.team.has(class_id=cls.id), Task.status == 'done').count()
            rate = round(done_t / total_t * 100) if total_t > 0 else 0
            report_q = DailyReport.query.filter(DailyReport.report_date == today,
                                                DailyReport.user_id.in_(cids)) if cids else DailyReport.query.filter(DailyReport.id == -1)
            report_rate = round(report_q.count() / len(cids) * 100) if cids else 0
            class_comparison.append({
                'name': cls.name, 'id': cls.id,
                'task_rate': rate, 'report_rate': report_rate,
                'student_count': len(cids)
            })

    # --- 最近动态 ---
    recent_reports = scope(DailyReport.query, DailyReport).order_by(DailyReport.submitted_at.desc()).limit(6).all()
    recent_tasks = scope(Task.query, Task).filter(Task.status.in_(['done', 'closed'])).order_by(Task.updated_at.desc()).limit(4).all()

    return render_template('dashboard/teacher.html',
                           user_classes=user_classes, selected_class=selected_class,
                           class_comparison=class_comparison,
                           missing_today=missing_today, missing_count=len(missing_today),
                           delayed_tasks=delayed_tasks, unreviewed_reports=unreviewed_reports,
                           pending_reviews=pending_reviews,
                           projects=projects, teams=teams, students=students_count,
                           tasks_total=tasks_total, tasks_done=tasks_by_status['done'],
                           tasks_delayed=delayed_tasks, bugs_total=bugs_total,
                           bugs_open=bugs_open, ai_count=ai_count,
                           deploy_rate=deploy_rate,
                           report_count=DailyReport.query.count(), reports_today=reports_today,
                           task_status_data=task_status_data,
                           team_ranking=team_ranking,
                           report_dates=report_dates, report_counts=report_counts,
                           recent_reports=recent_reports, recent_tasks=recent_tasks)


def admin_dashboard(today):
    """管理员专用仪表盘——系统全局管理视图"""
    classes = Class.query.filter_by(is_archived=False).count()
    classes_archived = Class.query.filter_by(is_archived=True).count()
    users_total = User.query.count()
    users_active = User.query.filter_by(is_active=True).count()
    students_count = User.query.filter(User.role.has(name='student')).count()
    teachers_count = User.query.filter(User.role.has(name='teacher')).count()
    projects_active = Project.query.filter(Project.status.in_(['not_started', 'in_progress'])).count()
    tasks_total = Task.query.count()
    tasks_done = Task.query.filter_by(status='done').count()
    bugs_open = Bug.query.filter(Bug.status.in_(['new', 'confirmed', 'fixing'])).count()
    reports_today = DailyReport.query.filter_by(report_date=today).count()
    system_logs_count = SystemLog.query.count()
    login_logs_today = LoginLog.query.filter(LoginLog.created_at >= today).count()

    # 班级概览
    class_overview = []
    for cls in Class.query.filter_by(is_archived=False).all():
        students = ClassMember.query.filter_by(class_id=cls.id, role_in_class='student').count()
        teachers = ClassMember.query.filter_by(class_id=cls.id, role_in_class='teacher').count()
        tasks_done_cls = Task.query.filter(Task.team.has(class_id=cls.id), Task.status == 'done').count()
        tasks_total_cls = Task.query.filter(Task.team.has(class_id=cls.id)).count()
        report_rate = 0
        class_student_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter_by(
            class_id=cls.id, role_in_class='student').all()]
        if class_student_ids:
            reports_today_cls = DailyReport.query.filter(
                DailyReport.report_date == today,
                DailyReport.user_id.in_(class_student_ids)
            ).count()
            report_rate = round(reports_today_cls / len(class_student_ids) * 100)
        class_overview.append({
            'id': cls.id, 'name': cls.name, 'students': students, 'teachers': teachers,
            'tasks_done': tasks_done_cls, 'tasks_total': tasks_total_cls,
            'report_rate': report_rate
        })

    # 最近操作日志
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(8).all()

    return render_template('dashboard/admin.html',
                           classes=classes, classes_archived=classes_archived,
                           users_total=users_total, users_active=users_active,
                           students_count=students_count, teachers_count=teachers_count,
                           projects_active=projects_active,
                           tasks_total=tasks_total, tasks_done=tasks_done,
                           bugs_open=bugs_open, reports_today=reports_today,
                           system_logs_count=system_logs_count,
                           login_logs_today=login_logs_today,
                           class_overview=class_overview,
                           recent_logs=recent_logs)


def student_dashboard(today, user_classes):
    # --- 班级信息 ---
    my_class = user_classes[0] if user_classes else None
    class_teachers = []
    class_student_count = 0
    if my_class:
        class_teachers = User.query.join(ClassMember).filter(
            ClassMember.class_id == my_class.id,
            ClassMember.role_in_class == 'teacher'
        ).all()
        class_student_count = ClassMember.query.filter_by(
            class_id=my_class.id, role_in_class='student').count()

    # --- 今日日报状态 ---
    today_report = DailyReport.query.filter_by(user_id=current_user.id, report_date=today).first()

    # --- 我的任务统计 ---
    my_tasks_total = Task.query.filter_by(assignee_id=current_user.id).count()
    my_tasks_done = Task.query.filter_by(assignee_id=current_user.id, status='done').count()
    my_tasks_in_progress = Task.query.filter_by(assignee_id=current_user.id, status='in_progress').count()
    my_tasks_todo = Task.query.filter_by(assignee_id=current_user.id, status='todo').count()
    my_tasks_delayed = Task.query.filter_by(assignee_id=current_user.id, status='delayed').count()
    completion_rate = round(my_tasks_done / my_tasks_total * 100) if my_tasks_total > 0 else 0

    # --- 紧急任务 ---
    urgent_date = today + timedelta(days=3)
    urgent_tasks = Task.query.filter(
        Task.assignee_id == current_user.id,
        Task.status.in_(['todo', 'in_progress', 'to_test']),
        Task.due_date != None,
        Task.due_date <= urgent_date
    ).order_by(Task.due_date.asc()).limit(8).all()

    # --- 我的Bug ---
    my_bugs = Bug.query.filter_by(assignee_id=current_user.id).filter(
        Bug.status.in_(['new', 'confirmed', 'fixing'])
    ).count()

    # --- 小组动态 ---
    my_team = None
    my_team_members = []
    team_activities = []
    membership = TeamMember.query.filter_by(user_id=current_user.id).first()
    if membership:
        my_team = membership.team
        my_team_members = TeamMember.query.filter_by(team_id=my_team.id).all()
        # Recent reports from team
        team_reports = DailyReport.query.filter(
            DailyReport.team_id == my_team.id
        ).order_by(DailyReport.submitted_at.desc()).limit(5).all()
        for r in team_reports:
            team_activities.append({
                'type': 'report',
                'user': r.user.real_name,
                'date': r.report_date.strftime('%m-%d') if r.report_date else '',
                'time': r.submitted_at.strftime('%H:%M') if r.submitted_at else ''
            })
        # Recent completed tasks from team
        team_done_tasks = Task.query.filter(
            Task.team_id == my_team.id,
            Task.status == 'done'
        ).order_by(Task.updated_at.desc()).limit(5).all()
        for t in team_done_tasks:
            team_activities.append({
                'type': 'task_done',
                'user': t.assignee.real_name if t.assignee else '未指派',
                'title': t.title,
                'time': t.updated_at.strftime('%m-%d %H:%M') if t.updated_at else ''
            })
        team_activities.sort(key=lambda x: x['time'], reverse=True)
        team_activities = team_activities[:8]

    # --- 班级动态（同班同学的活动） ---
    class_activities = []
    if my_class:
        class_student_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter_by(
            class_id=my_class.id, role_in_class='student').all()]
        if class_student_ids:
            class_reports = DailyReport.query.filter(
                DailyReport.user_id.in_(class_student_ids)
            ).order_by(DailyReport.submitted_at.desc()).limit(6).all()
            for r in class_reports:
                if r.user_id != current_user.id:
                    class_activities.append({
                        'type': 'report',
                        'user': r.user.real_name,
                        'time': r.submitted_at.strftime('%m-%d %H:%M') if r.submitted_at else ''
                    })

    # --- 我的数据 ---
    my_reports = DailyReport.query.filter_by(user_id=current_user.id).count()
    my_bugs_reported = Bug.query.filter_by(reporter_id=current_user.id).count()
    my_ai = AiRecord.query.filter_by(user_id=current_user.id).count()

    # --- 最近任务 ---
    my_recent_tasks = Task.query.filter_by(assignee_id=current_user.id).order_by(Task.updated_at.desc()).limit(6).all()

    # --- 公告 ---
    if my_class:
        announcements = Announcement.query.filter(
            or_(Announcement.class_id == None, Announcement.class_id == my_class.id)
        ).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(3).all()
    else:
        announcements = Announcement.query.filter(
            Announcement.class_id == None
        ).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(3).all()

    return render_template('dashboard/student.html',
                           today=today, today_report=today_report,
                           current_hour=dt.utcnow().hour + 8,
                           my_class=my_class, class_teachers=class_teachers,
                           class_student_count=class_student_count,
                           class_activities=class_activities,
                           my_tasks_total=my_tasks_total, my_tasks_done=my_tasks_done,
                           my_tasks_in_progress=my_tasks_in_progress,
                           completion_rate=completion_rate,
                           urgent_tasks=urgent_tasks,
                           my_bugs=my_bugs, my_team=my_team,
                           my_team_members=my_team_members,
                           team_activities=team_activities,
                           my_reports=my_reports, my_bugs_reported=my_bugs_reported,
                           my_ai=my_ai, my_recent_tasks=my_recent_tasks,
                           announcements=announcements)
