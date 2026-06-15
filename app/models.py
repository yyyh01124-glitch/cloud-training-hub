import bcrypt
from datetime import datetime
from sqlalchemy import func, Enum as SAEnum
from flask_login import UserMixin
from app.extensions import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    users = db.relationship('User', backref='role', lazy='dynamic', passive_deletes=True)


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), default='')
    phone = db.Column(db.String(20), default='')
    avatar = db.Column(db.String(255), default='')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    login_fail_count = db.Column(db.Integer, default=0)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    login_logs = db.relationship('LoginLog', backref='user', lazy='dynamic',
                                  foreign_keys='LoginLog.user_id', passive_deletes=True)
    daily_reports = db.relationship('DailyReport', backref='user', lazy='dynamic', passive_deletes=True)
    ai_records = db.relationship('AiRecord', backref='user', lazy='dynamic', passive_deletes=True)
    system_logs = db.relationship('SystemLog', backref='user', lazy='dynamic')
    reported_bugs = db.relationship('Bug', backref='reporter', lazy='dynamic',
                                     foreign_keys='Bug.reporter_id', passive_deletes=True)
    assigned_bugs = db.relationship('Bug', backref='assignee', lazy='dynamic',
                                     foreign_keys='Bug.assignee_id')
    assigned_tasks = db.relationship('Task', backref='assignee', lazy='dynamic',
                                      foreign_keys='Task.assignee_id')
    authored_announcements = db.relationship('Announcement', backref='publisher', lazy='dynamic',
                                              passive_deletes=True)
    taught_courses = db.relationship('Course', backref='teacher', lazy='dynamic')
    led_projects = db.relationship('Project', backref='leader', lazy='dynamic',
                                    foreign_keys='Project.leader_id')
    led_teams = db.relationship('Team', backref='leader', lazy='dynamic')
    team_memberships = db.relationship('TeamMember', backref='member', lazy='dynamic',
                                        passive_deletes=True)
    crawler_configs = db.relationship('CrawlerConfig', backref='creator', lazy='dynamic')
    scores_given = db.relationship('Score', backref='scorer', lazy='dynamic',
                                    foreign_keys='Score.scored_by', passive_deletes=True)
    scores_received = db.relationship('Score', backref='student', lazy='dynamic',
                                       foreign_keys='Score.student_id')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def __repr__(self):
        return f'<User {self.username}>'


class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = db.Column(db.String(45), default='')
    user_agent = db.Column(db.String(500), default='')
    is_success = db.Column(db.Boolean, default=False)
    fail_reason = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    projects = db.relationship('Project', backref='course', lazy='dynamic', passive_deletes=True)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    status = db.Column(
        SAEnum('not_started', 'in_progress', 'completed', 'archived', name='project_status'),
        default='not_started'
    )
    tech_stack = db.Column(db.String(500), default='')
    score_rule = db.Column(db.Text)
    deploy_url = db.Column(db.String(500), default='')
    git_repo_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    teams = db.relationship('Team', backref='project', lazy='dynamic', passive_deletes=True)
    tasks = db.relationship('Task', backref='project', lazy='dynamic', passive_deletes=True)
    scores = db.relationship('Score', backref='project', lazy='dynamic', passive_deletes=True)


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    description = db.Column(db.String(500), default='')
    deploy_url = db.Column(db.String(500), default='')
    doc_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    members = db.relationship('TeamMember', backref='team', lazy='dynamic', passive_deletes=True)
    tasks = db.relationship('Task', backref='team', lazy='dynamic')
    daily_reports = db.relationship('DailyReport', backref='team', lazy='dynamic')
    scores = db.relationship('Score', backref='team', lazy='dynamic', passive_deletes=True)


class TeamMember(db.Model):
    __tablename__ = 'team_members'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_in_team = db.Column(db.String(50), nullable=False, default='member')
    joined_at = db.Column(db.DateTime, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='uk_team_user'),
    )


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='SET NULL'))
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    priority = db.Column(
        SAEnum('high', 'medium', 'low', name='task_priority'),
        default='medium'
    )
    status = db.Column(
        SAEnum('todo', 'in_progress', 'to_test', 'done', 'delayed', 'closed', name='task_status'),
        default='todo'
    )
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    estimated_hours = db.Column(db.Numeric(5, 1), default=0)
    actual_hours = db.Column(db.Numeric(5, 1), default=0)
    completion_note = db.Column(db.Text)
    screenshot_url = db.Column(db.String(500), default='')
    related_bug_id = db.Column(db.Integer, db.ForeignKey('bugs.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    ai_records = db.relationship('AiRecord', backref='task', lazy='dynamic')


class DailyReport(db.Model):
    __tablename__ = 'daily_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='SET NULL'))
    report_date = db.Column(db.Date, nullable=False)
    completed_content = db.Column(db.Text)
    problems_encountered = db.Column(db.Text)
    ai_tools_used = db.Column(db.String(500), default='')
    ai_help_summary = db.Column(db.Text)
    code_commits = db.Column(db.Text)
    next_day_plan = db.Column(db.Text)
    self_score = db.Column(db.Integer, default=3)
    teacher_comment = db.Column(db.Text)
    is_excellent = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        db.UniqueConstraint('user_id', 'report_date', name='uk_user_date'),
    )


class Bug(db.Model):
    __tablename__ = 'bugs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    repro_steps = db.Column(db.Text)
    expected_result = db.Column(db.Text)
    actual_result = db.Column(db.Text)
    screenshot_url = db.Column(db.String(500), default='')
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    module = db.Column(db.String(100), default='')
    severity = db.Column(
        SAEnum('fatal', 'major', 'normal', 'minor', 'suggestion', name='bug_severity'),
        default='normal'
    )
    status = db.Column(
        SAEnum('new', 'confirmed', 'fixing', 'fixed', 'closed', 'wontfix', name='bug_status'),
        default='new'
    )
    solution = db.Column(db.Text)
    closed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    related_tasks = db.relationship('Task', backref='related_bug', lazy='dynamic',
                                     foreign_keys='Task.related_bug_id')


class CrawlerConfig(db.Model):
    __tablename__ = 'crawler_configs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    source_url = db.Column(db.String(1000), nullable=False)
    source_type = db.Column(
        SAEnum('job', 'tech_article', 'opensource', 'other', name='crawler_source_type'),
        default='tech_article'
    )
    keywords = db.Column(db.String(500), default='')
    cron_expr = db.Column(db.String(100), default='')
    is_active = db.Column(db.Boolean, default=True)
    request_interval = db.Column(db.Integer, default=3)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

    data_entries = db.relationship('CrawlerData', backref='config', lazy='dynamic')


class CrawlerData(db.Model):
    __tablename__ = 'crawler_data'
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('crawler_configs.id', ondelete='SET NULL'))
    title = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(1000), default='')
    summary = db.Column(db.Text)
    source_type = db.Column(
        SAEnum('job', 'tech_article', 'opensource', 'other', name='crawler_data_source_type'),
        default='tech_article'
    )
    keywords_matched = db.Column(db.String(300), default='')
    raw_data = db.Column(db.JSON)
    pub_date = db.Column(db.String(50), default='')
    data_hash = db.Column(db.String(64), default='', unique=True)
    created_at = db.Column(db.DateTime, server_default=func.now())


class AiRecord(db.Model):
    __tablename__ = 'ai_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='SET NULL'))
    tool_name = db.Column(db.String(100), nullable=False)
    scene = db.Column(db.String(100), nullable=False)
    scene_category = db.Column(
        SAEnum('db_design', 'flask_route', 'error_explain', 'style_optimize',
               'test_case', 'dockerfile', 'compose', 'deploy_doc', 'log_analysis',
               'project_summary', 'other', name='ai_scene_category'),
        default='other'
    )
    prompt_text = db.Column(db.Text)
    ai_output_summary = db.Column(db.Text)
    is_adopted = db.Column(db.Boolean, default=True)
    has_modified = db.Column(db.Boolean, default=False)
    modification_note = db.Column(db.Text)
    effect_description = db.Column(db.Text)
    related_files = db.Column(db.String(1000), default='')
    risk_note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())


class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    scored_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Numeric(5, 2), nullable=False)
    max_score = db.Column(db.Numeric(5, 2), default=100)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())


class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    action = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(100), default='')
    target_type = db.Column(db.String(50), default='')
    target_id = db.Column(db.Integer, default=0)
    detail = db.Column(db.JSON)
    ip_address = db.Column(db.String(45), default='')
    created_at = db.Column(db.DateTime, server_default=func.now())


class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text)
    publisher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=func.now())
    updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
