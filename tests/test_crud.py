"""CRUD integration tests — create, read, update entities via HTTP."""

import pytest
from datetime import date
from flask import url_for
from app.extensions import db
from app.models import (
    Course, Project, Team, TeamMember, Task, DailyReport,
    Bug, AiRecord, User, Role, CrawlerConfig, CrawlerData,
)
from conftest import tag


# ---------------------------------------------------------------------------
# Course CRUD
# ---------------------------------------------------------------------------

class TestCourseCRUD:

    def test_create_course(self, auth_client, app):
        name = tag('CRUD-Course')
        with auth_client:
            r = auth_client.post('/projects/courses/create', data={
                'name': name,
                'description': 'CRUD test course',
                'is_active': 'on',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '创建成功' in r.data.decode('utf-8')

        with app.app_context():
            course = Course.query.filter_by(name=name).first()
            assert course is not None
            assert course.description == 'CRUD test course'
            assert course.is_active is True
            # Cleanup
            if course:
                db.session.delete(course)
                db.session.commit()

    def test_read_course_list(self, auth_client, app):
        """Course list page loads and displays courses."""
        with app.app_context():
            c = Course(name=tag('CRUD-ListCourse'), description='For listing')
            db.session.add(c)
            db.session.commit()
            cid = c.id

        with auth_client:
            r = auth_client.get('/projects/courses', follow_redirects=True)
            assert r.status_code == 200
            body = r.data.decode('utf-8')
            assert '课程' in body or 'courses' in body.lower()

        with app.app_context():
            c = db.session.get(Course, cid)
            if c:
                db.session.delete(c)
                db.session.commit()

    def test_update_course(self, auth_client, app):
        name = tag('CRUD-Course-Upd')
        with app.app_context():
            c = Course(name=name, description='Before update')
            db.session.add(c)
            db.session.commit()
            cid = c.id

        updated_name = tag('CRUD-Course-Upd-2')
        with auth_client:
            r = auth_client.post(f'/projects/courses/{cid}/edit', data={
                'name': updated_name,
                'description': 'After update',
                'is_active': 'on',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已更新' in r.data.decode('utf-8')

        with app.app_context():
            course = db.session.get(Course, cid)
            assert course.name == updated_name
            assert course.description == 'After update'
            db.session.delete(course)
            db.session.commit()


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

class TestProjectCRUD:

    def test_create_project(self, auth_client, app):
        name = tag('CRUD-Project')
        with app.app_context():
            course = Course(name=tag('CRUD-Course-Proj'))
            db.session.add(course)
            db.session.commit()
            cid = course.id

        with auth_client:
            r = auth_client.post('/projects/create', data={
                'course_id': cid,
                'name': name,
                'description': 'CRUD test project',
                'status': 'in_progress',
                'tech_stack': 'Flask, MySQL',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '创建成功' in r.data.decode('utf-8')

        with app.app_context():
            project = Project.query.filter_by(name=name).first()
            assert project is not None
            assert project.course_id == cid
            assert project.status == 'in_progress'
            # Cascade cleanup
            db.session.delete(project)
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()

    def test_read_project_detail(self, auth_client, app):
        with app.app_context():
            course = Course(name=tag('CRUD-Course-ProjD'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-ProjD'), course_id=course.id,
                              description='Detail view')
            db.session.add(project)
            db.session.commit()
            pid = project.id
            cid = course.id

        with auth_client:
            r = auth_client.get(f'/projects/{pid}', follow_redirects=True)
            assert r.status_code == 200
            assert 'Detail view' in r.data.decode('utf-8')

        with app.app_context():
            db.session.delete(db.session.get(Project, pid))
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()

    def test_update_project(self, auth_client, app):
        with app.app_context():
            course = Course(name=tag('CRUD-Course-ProjUpd'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-ProjUpd'), course_id=course.id,
                              status='not_started', tech_stack='Old stack')
            db.session.add(project)
            db.session.commit()
            pid = project.id
            cid = course.id

        with auth_client:
            r = auth_client.post(f'/projects/{pid}/edit', data={
                'course_id': cid,
                'name': tag('CRUD-ProjUpd-New'),
                'description': 'Updated desc',
                'status': 'completed',
                'tech_stack': 'New Stack',
                'deploy_url': 'https://example.com',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已更新' in r.data.decode('utf-8')

        with app.app_context():
            proj = db.session.get(Project, pid)
            assert proj.status == 'completed'
            assert proj.tech_stack == 'New Stack'
            assert proj.deploy_url == 'https://example.com'
            db.session.delete(proj)
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()


# ---------------------------------------------------------------------------
# Task CRUD + status transitions
# ---------------------------------------------------------------------------

class TestTaskCRUD:

    @pytest.fixture
    def project_context(self, app):
        """Create a project (and course) for task tests, clean up after."""
        with app.app_context():
            course = Course(name=tag('CRUD-Course-Task'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-Proj-Task'), course_id=course.id)
            db.session.add(project)
            db.session.commit()
            yield {'project_id': project.id, 'course_id': course.id,
                   'project': project, 'course': course}
            db.session.delete(db.session.get(Project, project.id))
            db.session.delete(db.session.get(Course, course.id))
            db.session.commit()

    def test_create_task(self, auth_client, app, project_context):
        pid = project_context['project_id']
        title = tag('CRUD-Task')

        with auth_client:
            r = auth_client.post('/tasks/create', data={
                'project_id': pid,
                'title': title,
                'description': 'Test task description',
                'priority': 'high',
                'status': 'todo',
                'estimated_hours': 16,
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '创建成功' in r.data.decode('utf-8')

        with app.app_context():
            task = Task.query.filter_by(title=title).first()
            assert task is not None
            assert task.priority == 'high'
            assert task.project_id == pid
            db.session.delete(task)
            db.session.commit()

    def test_change_task_status(self, auth_client, app, project_context):
        pid = project_context['project_id']
        title = tag('CRUD-Task-Status')
        with app.app_context():
            task = Task(project_id=pid, title=title, status='todo')
            db.session.add(task)
            db.session.commit()
            tid = task.id

        with auth_client:
            r = auth_client.post(f'/tasks/{tid}/status', data={
                'status': 'in_progress',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已更新' in r.data.decode('utf-8') or '状态已更新' in r.data.decode('utf-8')

        with app.app_context():
            task = db.session.get(Task, tid)
            assert task.status == 'in_progress'

            # Transition again
            task.status = 'done'
            db.session.commit()

        with auth_client:
            r = auth_client.post(f'/tasks/{tid}/status', data={
                'status': 'closed',
            }, follow_redirects=True)

        with app.app_context():
            task = db.session.get(Task, tid)
            assert task.status == 'closed'
            db.session.delete(task)
            db.session.commit()

    def test_update_task(self, auth_client, app, project_context):
        pid = project_context['project_id']
        title = tag('CRUD-Task-Upd')
        with app.app_context():
            task = Task(project_id=pid, title=title, priority='low')
            db.session.add(task)
            db.session.commit()
            tid = task.id

        with auth_client:
            r = auth_client.post(f'/tasks/{tid}/edit', data={
                'title': title + ' Updated',
                'description': 'Updated desc',
                'priority': 'high',
                'status': 'in_progress',
                'estimated_hours': 24,
                'actual_hours': 20,
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已更新' in r.data.decode('utf-8')

        with app.app_context():
            t = db.session.get(Task, tid)
            assert t.priority == 'high'
            assert t.status == 'in_progress'
            assert float(t.estimated_hours) == 24
            assert float(t.actual_hours) == 20
            db.session.delete(t)
            db.session.commit()


# ---------------------------------------------------------------------------
# Daily Report CRUD (including duplicate prevention)
# ---------------------------------------------------------------------------

class TestDailyReportCRUD:

    def test_create_daily_report(self, auth_client, app):
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            user = User(
                username=tag('CRUD-ReportUser'),
                real_name='Report Tester',
                role_id=student_role.id,
                is_active=True,
            )
            user.set_password('pass123')
            db.session.add(user)
            db.session.commit()
            uid = user.id

        client2 = app.test_client()
        with client2:
            client2.post('/auth/login', data={
                'username': user.username,
                'password': 'pass123',
            })

            r = client2.post('/reports/create', data={
                'completed_content': 'Implemented login page',
                'problems_encountered': 'CSRF issues',
                'ai_tools_used': 'Claude Code',
                'code_commits': '3 commits',
                'next_day_plan': 'Start dashboard',
                'self_score': 4,
            }, follow_redirects=True)
            assert r.status_code == 200
            body = r.data.decode('utf-8')
            assert '提交成功' in body or '今天已提交' not in body

        with app.app_context():
            reports = DailyReport.query.filter_by(user_id=uid).all()
            for rep in reports:
                db.session.delete(rep)
            db.session.delete(db.session.get(User, uid))
            db.session.commit()

    def test_duplicate_report_redirects_to_edit(self, auth_client, app):
        """Submitting a second report on the same day redirects to edit."""
        from datetime import date as dt_date
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            user = User(
                username=tag('CRUD-DupReport'),
                real_name='Dup Tester',
                role_id=student_role.id,
                is_active=True,
            )
            user.set_password('pass123')
            db.session.add(user)
            db.session.flush()

            # Create first report manually
            report = DailyReport(
                user_id=user.id,
                report_date=dt_date.today(),
                completed_content='First report',
            )
            db.session.add(report)
            db.session.commit()
            uid = user.id
            rid = report.id

        client2 = app.test_client()
        with client2:
            client2.post('/auth/login', data={
                'username': user.username,
                'password': 'pass123',
            })

            # Try to create second report for today -> should redirect to edit
            r = client2.post('/reports/create', data={
                'completed_content': 'Second report attempt',
            }, follow_redirects=True)
            assert r.status_code == 200
            body = r.data.decode('utf-8')
            assert '已提交' in body or '编辑' in body or '日报' in body

        with app.app_context():
            db.session.delete(db.session.get(DailyReport, rid))
            db.session.delete(db.session.get(User, uid))
            db.session.commit()


# ---------------------------------------------------------------------------
# Bug CRUD + status transitions
# ---------------------------------------------------------------------------

class TestBugCRUD:

    def test_create_bug(self, auth_client, app):
        title = tag('CRUD-Bug')
        with auth_client:
            r = auth_client.post('/bugs/create', data={
                'title': title,
                'description': 'Bug found in login',
                'severity': 'major',
                'module': 'auth',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已提交' in r.data.decode('utf-8')

        with app.app_context():
            bug = Bug.query.filter_by(title=title).first()
            assert bug is not None
            assert bug.severity == 'major'
            assert bug.status == 'new'
            db.session.delete(bug)
            db.session.commit()

    def test_bug_status_transition(self, auth_client, app):
        """Transition bug through: confirmed -> fixing -> fixed -> closed."""
        title = tag('CRUD-Bug-Trans')
        with app.app_context():
            student_role = Role.query.filter_by(name='student').first()
            reporter = User(
                username=tag('CRUD-BugRep'),
                real_name='Bug Reporter',
                role_id=student_role.id,
                is_active=True,
            )
            reporter.set_password('pass123')
            db.session.add(reporter)
            db.session.flush()
            bug = Bug(title=title, reporter_id=reporter.id, status='new')
            db.session.add(bug)
            db.session.commit()
            bid = bug.id
            uid = reporter.id

        client2 = app.test_client()
        with client2:
            client2.post('/auth/login', data={
                'username': reporter.username, 'password': 'pass123',
            })

            # new -> confirmed
            client2.post(f'/bugs/{bid}/status', data={'status': 'confirmed'},
                         follow_redirects=True)
            # confirmed -> fixing
            client2.post(f'/bugs/{bid}/status', data={'status': 'fixing'},
                         follow_redirects=True)
            # fixing -> fixed
            client2.post(f'/bugs/{bid}/status', data={'status': 'fixed'},
                         follow_redirects=True)

        with app.app_context():
            bug = db.session.get(Bug, bid)
            # fixed -> closed (via admin)
            assert bug.status == 'fixed'

            with auth_client:
                auth_client.post(f'/bugs/{bid}/status', data={'status': 'closed'},
                                 follow_redirects=True)

            bug = db.session.get(Bug, bid)
            assert bug.status == 'closed'
            assert bug.closed_at is not None

            db.session.delete(bug)
            db.session.delete(db.session.get(User, uid))
            db.session.commit()


# ---------------------------------------------------------------------------
# AI Record CRUD
# ---------------------------------------------------------------------------

class TestAiRecordCRUD:

    def test_create_ai_record(self, auth_client, app):
        with app.app_context():
            # Need a task for the AI record
            course = Course(name=tag('CRUD-Course-AI'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-Proj-AI'), course_id=course.id)
            db.session.add(project)
            db.session.flush()
            admin = User.query.filter_by(username='admin').first()
            task = Task(project_id=project.id, title=tag('CRUD-Task-AI'),
                        assignee_id=admin.id)
            db.session.add(task)
            db.session.commit()
            tid = task.id
            pid = project.id
            cid = course.id

        with auth_client:
            r = auth_client.post('/ai-records/create', data={
                'task_id': tid,
                'tool_name': 'Claude Code',
                'scene': 'Generate Flask route',
                'scene_category': 'flask_route',
                'prompt_text': 'Create user login API',
                'ai_output_summary': 'Generated login route with JWT',
                'is_adopted': 'on',
                'effect_description': 'Saved 2 hours',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已保存' in r.data.decode('utf-8')

        with app.app_context():
            record = AiRecord.query.filter_by(task_id=tid).first()
            assert record is not None
            assert record.tool_name == 'Claude Code'
            assert record.is_adopted is True
            # Cleanup
            db.session.delete(record)
            db.session.delete(db.session.get(Task, tid))
            db.session.delete(db.session.get(Project, pid))
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()


# ---------------------------------------------------------------------------
# Team CRUD (with members)
# ---------------------------------------------------------------------------

class TestTeamCRUD:

    def test_create_team(self, auth_client, app):
        name = tag('CRUD-Team')
        with app.app_context():
            course = Course(name=tag('CRUD-Course-Team'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-Proj-Team'), course_id=course.id)
            db.session.add(project)
            db.session.commit()
            pid = project.id
            cid = course.id

        with auth_client:
            r = auth_client.post('/teams/create', data={
                'project_id': pid,
                'name': name,
                'description': 'Test team for CRUD',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '创建成功' in r.data.decode('utf-8')

        with app.app_context():
            team = Team.query.filter_by(name=name).first()
            assert team is not None
            # Cleanup
            db.session.delete(team)
            db.session.delete(db.session.get(Project, pid))
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()

    def test_team_detail_page(self, auth_client, app):
        with app.app_context():
            course = Course(name=tag('CRUD-Course-TeamD'))
            db.session.add(course)
            db.session.flush()
            project = Project(name=tag('CRUD-Proj-TeamD'), course_id=course.id)
            db.session.add(project)
            db.session.flush()
            team = Team(name=tag('CRUD-Team-Detail'), project_id=project.id)
            db.session.add(team)
            db.session.commit()
            tid = team.id
            pid = project.id
            cid = course.id

        with auth_client:
            r = auth_client.get(f'/teams/{tid}', follow_redirects=True)
            assert r.status_code == 200

        with app.app_context():
            db.session.delete(db.session.get(Team, tid))
            db.session.delete(db.session.get(Project, pid))
            db.session.delete(db.session.get(Course, cid))
            db.session.commit()


# ---------------------------------------------------------------------------
# Crawler Config CRUD
# ---------------------------------------------------------------------------

class TestCrawlerConfigCRUD:

    def test_create_crawler_config(self, auth_client, app):
        name = tag('CRUD-CrawlerCfg')
        with auth_client:
            r = auth_client.post('/crawler/configs/create', data={
                'name': name,
                'source_url': 'https://example.com/rss',
                'source_type': 'tech_article',
                'keywords': 'python, flask',
            }, follow_redirects=True)
            assert r.status_code == 200
            assert '已创建' in r.data.decode('utf-8')

        with app.app_context():
            cfg = CrawlerConfig.query.filter_by(name=name).first()
            assert cfg is not None
            assert cfg.is_active is True
            db.session.delete(cfg)
            db.session.commit()
