"""Authentication tests — login, logout, access control."""

import pytest
from flask import url_for, session
from app.extensions import db
from app.models import User, LoginLog, Role


class TestLogin:
    """Login flows."""

    def test_login_success(self, client):
        """Admin can log in with correct credentials and see welcome message."""
        with client:
            r = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'admin123',
            }, follow_redirects=True)
            assert r.status_code == 200
            body = r.data.decode('utf-8')
            assert '欢迎回来' in body

    def test_login_sets_session(self, client):
        """Login populates the session with the user id."""
        with client:
            client.post('/auth/login', data={
                'username': 'admin', 'password': 'admin123',
            })
            with client.session_transaction() as sess:
                assert '_user_id' in sess
                assert sess['_user_id'] is not None

    def test_login_wrong_password(self, client):
        """Login with wrong password shows error and does not create session."""
        with client:
            r = client.post('/auth/login', data={
                'username': 'admin',
                'password': 'wrongpass',
            }, follow_redirects=True)
            assert r.status_code == 200
            body = r.data.decode('utf-8')
            assert '用户名或密码错误' in body

            # No session created
            with client.session_transaction() as sess:
                assert '_user_id' not in sess or sess['_user_id'] is None

    def test_login_nonexistent_user(self, client):
        """Login with a non-existent username shows generic error."""
        with client:
            r = client.post('/auth/login', data={
                'username': 'nonexistent_user_xyz',
                'password': 'irrelevant',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '用户名或密码错误' in r.data.decode('utf-8')

    def test_login_empty_form(self, client):
        """Submitting empty login form shows error message."""
        with client:
            r = client.post('/auth/login', data={
                'username': '',
                'password': '',
            }, follow_redirects=True)
            assert r.status_code == 200
            # Should stay on login page
            assert '登录' in r.data.decode('utf-8')

    def test_login_logs_login_log(self, client, app):
        """Successful login creates a LoginLog record."""
        with client:
            client.post('/auth/login', data={
                'username': 'admin', 'password': 'admin123',
            })
        with app.app_context():
            log = LoginLog.query.filter_by(is_success=True).order_by(
                LoginLog.created_at.desc()).first()
            assert log is not None
            assert log.is_success is True
            assert log.user_id is not None

    def test_failed_login_records_fail_count(self, client, app):
        """Failed login increments login_fail_count."""
        with client:
            with app.app_context():
                admin = User.query.filter_by(username='admin').first()
                original_count = admin.login_fail_count or 0

            client.post('/auth/login', data={
                'username': 'admin', 'password': 'wrong',
            })

            with app.app_context():
                admin = User.query.filter_by(username='admin').first()
                assert admin.login_fail_count == original_count + 1


class TestLogout:
    """Logout flow."""

    def test_logout_clears_session(self, auth_client):
        """After logout the session no longer contains user id."""
        with auth_client:
            r = auth_client.get('/auth/logout', follow_redirects=True)
            assert r.status_code == 200
            assert '已退出登录' in r.data.decode('utf-8')

            with auth_client.session_transaction() as sess:
                assert '_user_id' not in sess or sess['_user_id'] is None

    def test_logout_redirects_to_login(self, auth_client):
        """Logout redirects to login page."""
        r = auth_client.get('/auth/logout')
        assert r.status_code == 302
        assert '/auth/login' in r.headers.get('Location', '')

    def test_access_after_logout_redirects(self, app, client):
        """After logging out, accessing dashboard redirects to login."""
        with client:
            client.post('/auth/login', data={
                'username': 'admin', 'password': 'admin123',
            })
            client.get('/auth/logout')
            r = client.get('/', follow_redirects=False)
            assert r.status_code == 302
            assert '/auth/login' in r.headers.get('Location', '')


class TestAccessControl:
    """Role-based page access."""

    def test_unauthenticated_redirect(self, client):
        """Unauthenticated users are redirected to login page."""
        r = client.get('/admin/users', follow_redirects=True)
        assert r.status_code == 200
        # Should land on login page
        assert '登录' in r.data.decode('utf-8')

    def test_admin_can_access_admin_pages(self, auth_client):
        """Admin user can access /admin/users."""
        with auth_client:
            r = auth_client.get('/admin/users', follow_redirects=True)
            assert r.status_code == 200

    def test_admin_can_access_dashboard(self, auth_client):
        """Admin user can access the dashboard."""
        with auth_client:
            r = auth_client.get('/', follow_redirects=True)
            assert r.status_code == 200

    def test_student_blocked_from_admin(self, client, app):
        """Student user receives 403 on /admin/users."""
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            student = User(
                username='test_student_blocked',
                real_name='Student Blocked',
                role_id=student_role.id,
                is_active=True,
            )
            student.set_password('pass123')
            db.session.add(student)
            db.session.commit()
            student_id = student.id

        with client:
            # Log in as student
            r = client.post('/auth/login', data={
                'username': 'test_student_blocked',
                'password': 'pass123',
            }, follow_redirects=True)
            assert r.status_code == 200

            # Try accessing admin
            r = client.get('/admin/users')
            assert r.status_code == 403

        # Cleanup
        with app.app_context():
            s = db.session.get(User, student_id)
            if s:
                db.session.delete(s)
                db.session.commit()

    def test_student_can_access_dashboard(self, client, app):
        """Student user can access their own dashboard (not 403)."""
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            student = User(
                username='test_student_dash',
                real_name='Student Dash',
                role_id=student_role.id,
                is_active=True,
            )
            student.set_password('pass123')
            db.session.add(student)
            db.session.commit()
            student_id = student.id

        with client:
            client.post('/auth/login', data={
                'username': 'test_student_dash',
                'password': 'pass123',
            })
            r = client.get('/', follow_redirects=True)
            # Should succeed, not 403
            assert r.status_code == 200

        with app.app_context():
            s = db.session.get(User, student_id)
            if s:
                db.session.delete(s)
                db.session.commit()

    def test_project_create_requires_admin_or_teacher(self, client, app):
        """Student cannot access project creation page."""
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            student = User(
                username='test_student_noproj',
                real_name='No Proj',
                role_id=student_role.id,
                is_active=True,
            )
            student.set_password('pass123')
            db.session.add(student)
            db.session.commit()
            student_id = student.id

        with client:
            client.post('/auth/login', data={
                'username': 'test_student_noproj',
                'password': 'pass123',
            })
            r = client.get('/projects/create')
            assert r.status_code == 403

        with app.app_context():
            s = db.session.get(User, student_id)
            if s:
                db.session.delete(s)
                db.session.commit()


class TestAuthenticatedRedirect:
    """Already-logged-in redirects."""

    def test_authenticated_user_redirected_from_login(self, auth_client):
        """Logged-in user visiting /auth/login gets redirected to dashboard."""
        with auth_client:
            r = auth_client.get('/auth/login', follow_redirects=True)
            assert r.status_code == 200
            # Should not see login page
            assert '登录' not in r.data.decode('utf-8') or r.request.path != '/auth/login'
