from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from app.extensions import db
from app.models import DailyReport, Team, ClassMember
from app.utils.decorators import log_activity, send_notification

report_bp = Blueprint('report', __name__)


@report_bp.route('/')
@login_required
def list_reports():
    page = request.args.get('page', 1, type=int)
    team_id = request.args.get('team_id', type=int)
    report_date = request.args.get('date', '')

    query = DailyReport.query
    if current_user.role.name == 'student':
        query = query.filter_by(user_id=current_user.id)
    elif current_user.role.name == 'teacher':
        # 教师只看自己班级学生的日报
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        student_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter(
            ClassMember.class_id.in_(class_ids), ClassMember.role_in_class == 'student').all()] if class_ids else []
        if student_ids:
            query = query.filter(DailyReport.user_id.in_(student_ids))
        else:
            query = query.filter(DailyReport.id == -1)  # no results
    if team_id:
        query = query.filter_by(team_id=team_id)
    if report_date:
        query = query.filter_by(report_date=report_date)

    reports = query.order_by(DailyReport.report_date.desc()).paginate(page=page, per_page=15)
    teams = Team.query.all() if current_user.role.name != 'student' else []
    return render_template('reports/list.html', reports=reports, teams=teams,
                           team_filter=team_id, date_filter=report_date)


@report_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_report():
    today = date.today()
    existing = DailyReport.query.filter_by(user_id=current_user.id, report_date=today).first()
    if existing:
        flash('今天已提交日报，可以编辑但不能重复创建', 'warning')
        return redirect(url_for('report.edit_report', report_id=existing.id))

    if request.method == 'POST':
        member = current_user.team_memberships.first()
        report = DailyReport(
            user_id=current_user.id,
            team_id=member.team_id if member else None,
            report_date=today,
            completed_content=request.form.get('completed_content', ''),
            problems_encountered=request.form.get('problems_encountered', ''),
            ai_tools_used=request.form.get('ai_tools_used', ''),
            ai_help_summary=request.form.get('ai_help_summary', ''),
            code_commits=request.form.get('code_commits', ''),
            next_day_plan=request.form.get('next_day_plan', ''),
            self_score=request.form.get('self_score', type=int) or 3
        )
        db.session.add(report)
        db.session.commit()
        log_activity('create', 'report', 'DailyReport', report.id, {'report_date': str(report.report_date)})
        # 通知班级教师
        from app.utils.decorators import send_notification as sn
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='student').all()]
        if class_ids:
            teacher_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter(
                ClassMember.class_id.in_(class_ids), ClassMember.role_in_class == 'teacher').all()]
            for tid in teacher_ids:
                sn(tid, 'report_submitted', f'{current_user.real_name} 提交了日报',
                   f'{current_user.real_name} 提交了 {today} 的日报', url_for('report.list_reports'))
        flash('日报提交成功', 'success')
        return redirect(url_for('report.list_reports'))
    return render_template('reports/form.html')


@report_bp.route('/<int:report_id>')
@login_required
def report_detail(report_id):
    report = db.session.get(DailyReport, report_id)
    if not report:
        flash('日报不存在', 'danger')
        return redirect(url_for('report.list_reports'))
    return render_template('reports/detail.html', report=report)


@report_bp.route('/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    report = db.session.get(DailyReport, report_id)
    if not report:
        flash('日报不存在', 'danger')
        return redirect(url_for('report.list_reports'))
    if current_user.role.name == 'student' and report.user_id != current_user.id:
        flash('只能编辑自己的日报', 'danger')
        return redirect(url_for('report.list_reports'))
    # 学生只能编辑当天的日报
    if current_user.role.name == 'student' and report.report_date != date.today():
        flash('只能编辑当天的日报', 'danger')
        return redirect(url_for('report.list_reports'))

    if request.method == 'POST':
        report.completed_content = request.form.get('completed_content', '')
        report.problems_encountered = request.form.get('problems_encountered', '')
        report.ai_tools_used = request.form.get('ai_tools_used', '')
        report.ai_help_summary = request.form.get('ai_help_summary', '')
        report.code_commits = request.form.get('code_commits', '')
        report.next_day_plan = request.form.get('next_day_plan', '')
        report.self_score = request.form.get('self_score', type=int) or 3
        db.session.commit()
        flash('日报已更新', 'success')
        return redirect(url_for('report.report_detail', report_id=report.id))
    return render_template('reports/form.html', report=report)


@report_bp.route('/<int:report_id>/review', methods=['GET', 'POST'])
@login_required
def review_report(report_id):
    if current_user.role.name not in ('admin', 'teacher'):
        flash('无权限', 'danger')
        return redirect(url_for('report.list_reports'))
    report = db.session.get(DailyReport, report_id)
    if not report:
        flash('日报不存在', 'danger')
        return redirect(url_for('report.list_reports'))
    # 教师只能点评自己班级学生的日报
    if current_user.role.name == 'teacher':
        student_class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=report.user_id, role_in_class='student').all()]
        teacher_class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        if not set(student_class_ids) & set(teacher_class_ids):
            flash('你只能点评自己班级学生的日报', 'danger')
            return redirect(url_for('report.list_reports'))
    if request.method == 'POST':
        report.teacher_comment = request.form.get('teacher_comment', '')
        report.is_excellent = request.form.get('is_excellent') == 'on'
        db.session.commit()
        log_activity('review', 'report', 'DailyReport', report.id, {'is_excellent': request.form.get('is_excellent') == 'on'})
        send_notification(report.user_id, 'report_reviewed', f'日报已被点评',
                          f'教师点评了你 {report.report_date} 的日报', url_for('report.report_detail', report_id=report.id))
        flash('点评已保存', 'success')
        return redirect(url_for('report.report_detail', report_id=report.id))
    return render_template('reports/review.html', report=report)


@report_bp.route('/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    report = db.session.get(DailyReport, report_id)
    if not report:
        flash('日报不存在', 'danger')
        return redirect(url_for('report.list_reports'))
    if current_user.role.name == 'student' and report.user_id != current_user.id:
        flash('只能删除自己的日报', 'danger')
        return redirect(url_for('report.list_reports'))
    db.session.delete(report)
    db.session.commit()
    flash('日报已删除', 'success')
    return redirect(url_for('report.list_reports'))


@report_bp.route('/missing')
@login_required
def missing_reports():
    if current_user.role.name not in ('admin', 'teacher'):
        return redirect(url_for('report.list_reports'))
    from datetime import date
    from app.models import User
    today = date.today()
    # 教师只看自己班级的学生
    if current_user.role.name == 'teacher':
        class_ids = [m[0] for m in db.session.query(ClassMember.class_id).filter_by(
            user_id=current_user.id, role_in_class='teacher').all()]
        student_ids = [m[0] for m in db.session.query(ClassMember.user_id).filter(
            ClassMember.class_id.in_(class_ids), ClassMember.role_in_class == 'student').all()] if class_ids else []
        students = User.query.filter(User.id.in_(student_ids), User.is_active == True).all() if student_ids else []
    else:
        students = User.query.filter(User.role.has(name='student'), User.is_active == True).all()
    missing = []
    for s in students:
        r = DailyReport.query.filter_by(user_id=s.id, report_date=today).first()
        if not r:
            last_rpt = DailyReport.query.filter_by(user_id=s.id).order_by(DailyReport.report_date.desc()).first()
            tm = s.team_memberships.first()
            missing.append({
                'user': s,
                'team_name': tm.team.name if tm and tm.team else '未加入小组',
                'last_date': last_rpt.report_date if last_rpt else None
            })
    return render_template('reports/missing.html', missing=missing, today=today)


@report_bp.route('/stats')
@login_required
def stats():
    if current_user.role.name not in ('admin', 'teacher'):
        return redirect(url_for('report.list_reports'))
    from app.models import User
    students = User.query.filter(User.role.has(name='student')).filter(User.is_active == True).all()
    stats_data = []
    for s in students:
        total = DailyReport.query.filter_by(user_id=s.id).count()
        stats_data.append({'name': s.real_name, 'count': total})
    return render_template('reports/stats.html', stats_data=stats_data)
