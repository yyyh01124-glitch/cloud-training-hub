from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import Task, Bug, DailyReport, Team, User

search_bp = Blueprint('search', __name__)


@search_bp.route('/')
@login_required
def global_search():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify({'results': []})

    results = []

    # 搜索任务
    task_query = Task.query
    if current_user.role.name == 'student':
        from app.models import TeamMember as TM
        my_team_ids = [t[0] for t in db.session.query(TM.team_id).filter_by(user_id=current_user.id).all()]
        task_query = task_query.filter(
            or_(Task.assignee_id == current_user.id,
                Task.team_id.in_(my_team_ids))
        )
    tasks = task_query.filter(Task.title.contains(q)).limit(5).all()
    for t in tasks:
        results.append({
            'type': 'task', 'title': t.title,
            'desc': f'{t.project.name if t.project else ""} | {t.assignee.real_name if t.assignee else ""}',
            'url': url_for('task.task_detail', task_id=t.id), 'badge': t.status
        })

    # 搜索Bug
    bugs = Bug.query.filter(Bug.title.contains(q)).limit(5).all()
    for b in bugs:
        results.append({
            'type': 'bug', 'title': b.title,
            'desc': f'{b.module} | {b.severity}',
            'url': url_for('bug.bug_detail', bug_id=b.id), 'badge': b.status
        })

    # 搜索日报（仅教师/管理员或自己的）
    report_query = DailyReport.query
    if current_user.role.name == 'student':
        report_query = report_query.filter_by(user_id=current_user.id)
    reports = report_query.filter(
        or_(DailyReport.completed_content.contains(q),
            DailyReport.problems_encountered.contains(q))
    ).limit(5).all()
    for r in reports:
        results.append({
            'type': 'report', 'title': f'{r.user.real_name} 的日报',
            'desc': (r.completed_content or '')[:80] + ('...' if r.completed_content and len(r.completed_content) > 80 else ''),
            'url': url_for('report.report_detail', report_id=r.id), 'badge': str(r.report_date)
        })

    # 搜索小组
    teams = Team.query.filter(Team.name.contains(q)).limit(3).all()
    for t in teams:
        results.append({
            'type': 'team', 'title': t.name,
            'desc': t.project.name if t.project else '',
            'url': url_for('team.team_detail', team_id=t.id), 'badge': ''
        })

    return jsonify({'results': results[:20]})
