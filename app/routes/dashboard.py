from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models import Project, Team, Task, User, Bug, DailyReport, AiRecord

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role.name == 'student':
        return student_dashboard()
    return teacher_dashboard()


def teacher_dashboard():
    projects = Project.query.all()
    teams = Team.query.all()
    students = User.query.filter(User.role.has(name='student')).count()
    tasks_total = Task.query.count()
    tasks_done = Task.query.filter_by(status='done').count()
    tasks_delayed = Task.query.filter_by(status='delayed').count()
    bugs_total = Bug.query.count()
    bugs_open = Bug.query.filter(Bug.status.in_(['new', 'confirmed', 'fixing'])).count()
    ai_count = AiRecord.query.count()
    report_count = DailyReport.query.count()
    reports_today = DailyReport.query.filter(DailyReport.report_date == __import__('datetime').date.today()).count()

    task_status_data = [
        {'name': '待开始', 'value': Task.query.filter_by(status='todo').count()},
        {'name': '进行中', 'value': Task.query.filter_by(status='in_progress').count()},
        {'name': '待测试', 'value': Task.query.filter_by(status='to_test').count()},
        {'name': '已完成', 'value': tasks_done},
        {'name': '已延期', 'value': tasks_delayed},
    ]

    bug_severity_data = [
        {'name': '致命', 'value': Bug.query.filter_by(severity='fatal').count()},
        {'name': '严重', 'value': Bug.query.filter_by(severity='major').count()},
        {'name': '一般', 'value': Bug.query.filter_by(severity='normal').count()},
        {'name': '轻微', 'value': Bug.query.filter_by(severity='minor').count()},
    ]

    # Team ranking
    team_ranking = []
    for t in teams:
        done = Task.query.filter_by(team_id=t.id, status='done').count()
        total_t = Task.query.filter_by(team_id=t.id).count()
        rate = round(done / total_t * 100) if total_t > 0 else 0
        team_ranking.append({'name': t.name, 'done': done, 'total': total_t, 'rate': rate})
    team_ranking.sort(key=lambda x: x['rate'], reverse=True)

    # Daily report line chart data (last 7 days)
    from datetime import timedelta
    report_dates = []
    report_counts = []
    for i in range(6, -1, -1):
        d = __import__('datetime').date.today() - timedelta(days=i)
        report_dates.append(d.strftime('%m-%d'))
        report_counts.append(DailyReport.query.filter_by(report_date=d).count())

    return render_template('dashboard/teacher.html',
                           projects=projects, teams=teams, students=students,
                           tasks_total=tasks_total, tasks_done=tasks_done,
                           tasks_delayed=tasks_delayed, bugs_total=bugs_total,
                           bugs_open=bugs_open, ai_count=ai_count,
                           report_count=report_count, reports_today=reports_today,
                           task_status_data=task_status_data,
                           bug_severity_data=bug_severity_data,
                           team_ranking=team_ranking,
                           report_dates=report_dates,
                           report_counts=report_counts)


def student_dashboard():
    my_tasks_total = Task.query.filter_by(assignee_id=current_user.id).count()
    my_tasks_done = Task.query.filter_by(assignee_id=current_user.id, status='done').count()
    my_reports = DailyReport.query.filter_by(user_id=current_user.id).count()
    my_bugs = Bug.query.filter_by(reporter_id=current_user.id).count()
    my_ai = AiRecord.query.filter_by(user_id=current_user.id).count()

    my_tasks = Task.query.filter_by(assignee_id=current_user.id).order_by(Task.due_date.asc()).limit(10).all()

    return render_template('dashboard/student.html',
                           my_tasks_total=my_tasks_total,
                           my_tasks_done=my_tasks_done,
                           my_reports=my_reports, my_bugs=my_bugs,
                           my_ai=my_ai, my_tasks=my_tasks)
