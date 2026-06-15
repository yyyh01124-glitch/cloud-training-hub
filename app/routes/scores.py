from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Score, Project, Team, User
from app.utils.decorators import teacher_or_admin

score_bp = Blueprint('score', __name__)


@score_bp.route('/')
@login_required
@teacher_or_admin
def list_scores():
    page = request.args.get('page', 1, type=int)
    project_id = request.args.get('project_id', type=int)
    team_id = request.args.get('team_id', type=int)
    query = Score.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    if team_id:
        query = query.filter_by(team_id=team_id)
    scores = query.order_by(Score.created_at.desc()).paginate(page=page, per_page=15)
    projects = Project.query.order_by(Project.name).all()
    teams = Team.query.order_by(Team.name).all()
    return render_template('scores/list.html', scores=scores, projects=projects, teams=teams,
                           filter_project=project_id, filter_team=team_id)


@score_bp.route('/create', methods=['GET', 'POST'])
@login_required
@teacher_or_admin
def create_score():
    if request.method == 'POST':
        score = Score(
            project_id=request.form.get('project_id', type=int),
            team_id=request.form.get('team_id', type=int),
            student_id=request.form.get('student_id', type=int) or None,
            scored_by=current_user.id,
            category=request.form.get('category', '').strip(),
            score=request.form.get('score', type=float) or 0,
            max_score=request.form.get('max_score', type=float) or 100,
            comment=request.form.get('comment', '')
        )
        db.session.add(score)
        db.session.commit()
        flash('评分已添加', 'success')
        return redirect(url_for('score.list_scores'))
    projects = Project.query.order_by(Project.name).all()
    teams = Team.query.order_by(Team.name).all()
    students = User.query.filter(User.role.has(name='student'), User.is_active == True).all()
    return render_template('scores/form.html', projects=projects, teams=teams, students=students)


@score_bp.route('/<int:score_id>/delete', methods=['POST'])
@login_required
@teacher_or_admin
def delete_score(score_id):
    score = db.session.get(Score, score_id)
    if score:
        db.session.delete(score)
        db.session.commit()
        flash('评分已删除', 'success')
    return redirect(url_for('score.list_scores'))
