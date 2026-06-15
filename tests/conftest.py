import os
import time
import uuid

os.environ['FLASK_CONFIG'] = 'development'
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:123456@localhost:3306/cloud_training_hub'
os.environ['SECRET_KEY'] = 'test'

import pytest
from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Course, Project, Team, TeamMember,
    Task, DailyReport, Bug, CrawlerConfig, CrawlerData,
    AiRecord, Score, Announcement, SystemLog, LoginLog
)

# Unique tag for this test session to avoid collisions
SESSION_TAG = f"TEST{uuid.uuid4().hex[:6]}"


def tag(base: str) -> str:
    """Tag a test entity name with the session tag for traceability."""
    return f"[{SESSION_TAG}] {base}"


# ---------------------------------------------------------------------------
# App and client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def app():
    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False
    application.config['SERVER_NAME'] = 'localhost'
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Return a test client already logged in as admin."""
    with client:
        r = client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert '欢迎回来' in r.data.decode('utf-8')
    return client


# ---------------------------------------------------------------------------
# Database session fixture (auto-rollback via savepoint)
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session(app):
    """Provide a DB session that rolls back after every test.

    All changes made inside ``flush()`` are visible within the test but
    never permanently committed to the database.
    """
    with app.app_context():
        db.session.begin_nested()
        yield db.session
        db.session.rollback()
        db.session.remove()


# ---------------------------------------------------------------------------
# Per-session role / admin seed (idempotent)
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session', autouse=True)
def seed_roles_and_admin(app):
    """Ensure Role and admin User exist before any test runs.

    Runs once per test session.
    """
    with app.app_context():
        existing = Role.query.count()
        if existing == 0:
            for r in ('admin', 'teacher', 'student'):
                db.session.add(Role(name=r, display_name=r.capitalize()))
            db.session.commit()

        if not User.query.filter_by(username='admin').first():
            admin_role = Role.query.filter_by(name='admin').first()
            admin = User(
                username='admin',
                real_name='Administrator',
                role_id=admin_role.id,
                is_active=True,
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()


# ---------------------------------------------------------------------------
# Helpers used across test modules
# ---------------------------------------------------------------------------

def create_test_course(db_session, name=None):
    """Create a minimal Course (committed)."""
    if name is None:
        name = tag('Course')
    role_teacher = Role.query.filter_by(name='teacher').first()
    teacher = User.query.filter_by(role_id=role_teacher.id).first()
    c = Course(name=name, teacher_id=teacher.id if teacher else None)
    db_session.add(c)
    db_session.flush()
    return c


def create_test_project(db_session, course=None, name=None):
    """Create a minimal Project (committed)."""
    if name is None:
        name = tag('Project')
    if course is None:
        course = create_test_course(db_session, tag('Course-Proj'))
    p = Project(name=name, course_id=course.id, status='in_progress')
    db_session.add(p)
    db_session.flush()
    return p


def create_test_team(db_session, project=None, name=None):
    """Create a minimal Team (committed)."""
    if name is None:
        name = tag('Team')
    if project is None:
        project = create_test_project(db_session)
    t = Team(name=name, project_id=project.id)
    db_session.add(t)
    db_session.flush()
    return t


def create_test_user(db_session, role_name='student', username=None):
    """Create a disposable User (committed)."""
    if username is None:
        username = tag(f'User{uuid.uuid4().hex[:4]}')
    role = Role.query.filter_by(name=role_name).first()
    u = User(username=username, real_name=f'Test {role_name}',
             role_id=role.id, is_active=True)
    u.set_password('testpass')
    db_session.add(u)
    db_session.flush()
    return u
