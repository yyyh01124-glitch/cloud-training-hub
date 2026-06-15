from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime

from app.extensions import db
from app.models import Course, Project, User, Team
from app.utils.decorators import teacher_or_admin

project_bp = Blueprint('project', __name__)


@project_bp.route('/courses')
@login_required
def list_courses():
    page = request.args.get('page', 1, type=int)
    query = Course.query
    if current_user.role.name == 'teacher':
        query = query.filter_by(teacher_id=current_user.id)
    courses = query.order_by(Course.created_at.desc()).paginate(page=page, per_page=12)
    return render_template('projects/courses.html', courses=courses)


@project_bp.route('/courses/create', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def create_course():
    if request.method == 'POST':
        course = Course(
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', ''),
            teacher_id=request.form.get('teacher_id', type=int) or current_user.id,
            start_date=request.form.get('start_date') or None,
            end_date=request.form.get('end_date') or None,
            is_active=request.form.get('is_active') == 'on'
        )
        db.session.add(course)
        db.session.commit()
        flash('课程创建成功', 'success')
        return redirect(url_for('project.list_courses'))
    teachers = User.query.filter(User.role.has(name='teacher')).all()
    return render_template('projects/course_form.html', teachers=teachers)


@project_bp.route('/courses/<int:course_id>')
@login_required
def course_detail(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('课程不存在', 'danger')
        return redirect(url_for('project.list_courses'))
    projects = Project.query.filter_by(course_id=course_id).order_by(Project.created_at.desc()).all()
    return render_template('projects/course_detail.html', course=course, projects=projects)


@project_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def edit_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('课程不存在', 'danger')
        return redirect(url_for('project.list_courses'))
    if request.method == 'POST':
        course.name = request.form.get('name', '').strip()
        course.description = request.form.get('description', '')
        course.teacher_id = request.form.get('teacher_id', type=int) or current_user.id
        course.start_date = request.form.get('start_date') or None
        course.end_date = request.form.get('end_date') or None
        course.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash('课程已更新', 'success')
        return redirect(url_for('project.course_detail', course_id=course.id))
    teachers = User.query.filter(User.role.has(name='teacher')).all()
    return render_template('projects/course_form.html', course=course, teachers=teachers)


@project_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@teacher_or_admin
def delete_course(course_id):
    course = db.session.get(Course, course_id)
    if course:
        db.session.delete(course)
        db.session.commit()
        flash('课程已删除', 'success')
    return redirect(url_for('project.list_courses'))


@project_bp.route('/')
@login_required
def list_projects():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Project.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    projects = query.order_by(Project.created_at.desc()).paginate(page=page, per_page=12)
    return render_template('projects/list.html', projects=projects, status_filter=status_filter)


@project_bp.route('/create', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def create_project():
    if request.method == 'POST':
        project = Project(
            course_id=request.form.get('course_id', type=int),
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', ''),
            leader_id=request.form.get('leader_id', type=int) or None,
            start_date=request.form.get('start_date') or None,
            end_date=request.form.get('end_date') or None,
            status=request.form.get('status', 'not_started'),
            tech_stack=request.form.get('tech_stack', ''),
            score_rule=request.form.get('score_rule', ''),
            deploy_url=request.form.get('deploy_url', ''),
            git_repo_url=request.form.get('git_repo_url', '')
        )
        db.session.add(project)
        db.session.commit()
        flash('项目创建成功', 'success')
        return redirect(url_for('project.list_projects'))
    courses = Course.query.filter_by(is_active=True).all()
    teachers = User.query.filter(User.role.has(name='teacher')).all()
    return render_template('projects/project_form.html', courses=courses, teachers=teachers)


@project_bp.route('/<int:project_id>')
@login_required
def project_detail(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        flash('项目不存在', 'danger')
        return redirect(url_for('project.list_projects'))
    teams = Team.query.filter_by(project_id=project_id).all()
    return render_template('projects/detail.html', project=project, teams=teams)


@project_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def edit_project(project_id):
    project = db.session.get(Project, project_id)
    if not project:
        flash('项目不存在', 'danger')
        return redirect(url_for('project.list_projects'))
    if request.method == 'POST':
        project.course_id = request.form.get('course_id', type=int)
        project.name = request.form.get('name', '').strip()
        project.description = request.form.get('description', '')
        project.leader_id = request.form.get('leader_id', type=int) or None
        project.start_date = request.form.get('start_date') or None
        project.end_date = request.form.get('end_date') or None
        project.status = request.form.get('status', 'not_started')
        project.tech_stack = request.form.get('tech_stack', '')
        project.score_rule = request.form.get('score_rule', '')
        project.deploy_url = request.form.get('deploy_url', '')
        project.git_repo_url = request.form.get('git_repo_url', '')
        db.session.commit()
        flash('项目已更新', 'success')
        return redirect(url_for('project.project_detail', project_id=project.id))
    courses = Course.query.filter_by(is_active=True).all()
    teachers = User.query.filter(User.role.has(name='teacher')).all()
    return render_template('projects/project_form.html', project=project, courses=courses, teachers=teachers)


@project_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
@teacher_or_admin
def delete_project(project_id):
    project = db.session.get(Project, project_id)
    if project:
        db.session.delete(project)
        db.session.commit()
        flash('项目已删除', 'success')
    return redirect(url_for('project.list_projects'))
