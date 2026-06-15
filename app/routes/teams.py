from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Team, TeamMember, Project, User

team_bp = Blueprint('team', __name__)


@team_bp.route('/')
@login_required
def list_teams():
    page = request.args.get('page', 1, type=int)
    project_id = request.args.get('project_id', type=int)
    query = Team.query
    if project_id:
        query = query.filter_by(project_id=project_id)
    teams = query.order_by(Team.created_at.desc()).paginate(page=page, per_page=12)
    projects = Project.query.all()
    return render_template('teams/list.html', teams=teams, projects=projects, project_filter=project_id)


@team_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_team():
    if request.method == 'POST':
        project_id = request.form.get('project_id', type=int)
        existing = TeamMember.query.join(Team).filter(
            Team.project_id == project_id,
            TeamMember.user_id == current_user.id
        ).first()
        if existing and current_user.role.name == 'student':
            flash('你已在该项目的另一个小组中', 'danger')
            return redirect(url_for('team.list_teams'))

        team = Team(
            project_id=project_id,
            name=request.form.get('name', '').strip(),
            description=request.form.get('description', '')
        )
        db.session.add(team)
        db.session.flush()
        member = TeamMember(team_id=team.id, user_id=current_user.id, role_in_team='leader')
        team.leader_id = current_user.id
        db.session.add(member)
        db.session.commit()
        flash('小组创建成功', 'success')
        return redirect(url_for('team.team_detail', team_id=team.id))
    projects = Project.query.all()
    return render_template('teams/form.html', projects=projects)


@team_bp.route('/<int:team_id>')
@login_required
def team_detail(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
    return render_template('teams/detail.html', team=team)


@team_bp.route('/<int:team_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        flash('小组不存在', 'danger')
        return redirect(url_for('team.list_teams'))
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
    existing = TeamMember.query.filter_by(team_id=team_id, user_id=current_user.id).first()
    if existing:
        flash('你已在此小组中', 'warning')
        return redirect(url_for('team.team_detail', team_id=team_id))
    project_member = TeamMember.query.join(Team).filter(
        Team.project_id == team.project_id,
        TeamMember.user_id == current_user.id
    ).first()
    if project_member:
        flash('你已在该项目的其他小组中', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    member = TeamMember(team_id=team_id, user_id=current_user.id, role_in_team='member')
    db.session.add(member)
    db.session.commit()
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
    db.session.delete(member)
    db.session.commit()
    flash('已退出小组', 'success')
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
        db.session.delete(member)
        db.session.commit()
        flash('成员已移除', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/members/<int:user_id>/role', methods=['POST'])
@login_required
def change_member_role(team_id, user_id):
    new_role = request.form.get('role_in_team', 'member')
    member = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
    if not member:
        flash('成员不存在', 'danger')
        return redirect(url_for('team.team_detail', team_id=team_id))
    team = db.session.get(Team, team_id)
    if new_role == 'leader':
        old_leader = TeamMember.query.filter_by(team_id=team_id, role_in_team='leader').first()
        if old_leader:
            old_leader.role_in_team = 'member'
        team.leader_id = user_id
        member.role_in_team = 'leader'
    else:
        member.role_in_team = new_role
    db.session.commit()
    flash('角色已更新', 'success')
    return redirect(url_for('team.team_detail', team_id=team_id))


@team_bp.route('/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    team = db.session.get(Team, team_id)
    if team and current_user.role.name in ('admin', 'teacher'):
        db.session.delete(team)
        db.session.commit()
        flash('小组已删除', 'success')
    return redirect(url_for('team.list_teams'))
