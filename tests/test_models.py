"""Model unit tests — verify model creation, hashing, and relationships."""

import pytest
from datetime import date, datetime
from app.extensions import db
from app.models import (
    User, Role, Course, Project, Team, TeamMember,
    Task, DailyReport, Bug, AiRecord, CrawlerConfig,
    CrawlerData, Score, Announcement, SystemLog,
)


class TestPasswordHashing:
    """User password hashing and verification."""

    def test_set_and_check_password(self, db_session):
        role = Role.query.filter_by(name='student').first()
        user = User(username='pwdtest1', real_name='Pwd Test',
                    role_id=role.id, email='pwd@test.com')
        user.set_password('MyS3cret!')

        assert user.password_hash is not None
        assert user.password_hash != ''  # not empty
        assert user.check_password('MyS3cret!') is True

    def test_wrong_password_fails(self, db_session):
        role = Role.query.filter_by(name='student').first()
        user = User(username='pwdtest2', real_name='Pwd Test 2',
                    role_id=role.id)
        user.set_password('correct')
        assert user.check_password('wrong') is False
        assert user.check_password('') is False

    def test_rehash_changes_hash(self, db_session):
        role = Role.query.filter_by(name='student').first()
        user = User(username='pwdtest3', real_name='Pwd Test 3',
                    role_id=role.id)
        user.set_password('first')
        first_hash = user.password_hash
        user.set_password('second')
        assert user.password_hash != first_hash
        assert user.check_password('second') is True
        assert user.check_password('first') is False


class TestUserModel:
    """User model fields, defaults, and relationships."""

    def test_create_user(self, db_session):
        role = Role.query.filter_by(name='student').first()
        user = User(
            username='jdoe',
            real_name='John Doe',
            email='john@example.com',
            phone='13800138000',
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        db_session.flush()

        retrieved = db_session.get(User, user.id)
        assert retrieved.username == 'jdoe'
        assert retrieved.real_name == 'John Doe'
        assert retrieved.email == 'john@example.com'
        assert retrieved.login_fail_count == 0
        assert retrieved.is_active is True
        assert retrieved.created_at is not None

    def test_user_role_relationship(self, db_session):
        admin_role = Role.query.filter_by(name='admin').first()
        user = User(username='rolelink', real_name='Role Link',
                    role_id=admin_role.id)
        db_session.add(user)
        db_session.flush()

        assert user.role.name == 'admin'
        assert user.role.display_name == 'Admin'

    def test_user_repr(self, db_session):
        role = Role.query.filter_by(name='student').first()
        user = User(username='reprtest', real_name='Repr', role_id=role.id)
        assert repr(user) == '<User reprtest>'


class TestCourseModel:
    """Course model."""

    def test_create_course(self, db_session):
        teacher_role = Role.query.filter_by(name='teacher').first()
        teacher = User(username='course_teacher', real_name='Teacher',
                       role_id=teacher_role.id)
        db_session.add(teacher)
        db_session.flush()

        course = Course(
            name='Python Web Development',
            description='Build web apps with Flask',
            teacher_id=teacher.id,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 7, 1),
            is_active=True,
        )
        db_session.add(course)
        db_session.flush()

        assert course.id is not None
        assert course.teacher.id == teacher.id
        assert course.is_active is True
        assert course.projects.count() == 0

    def test_course_defaults(self, db_session):
        course = Course(name='Defaults Course')
        db_session.add(course)
        db_session.flush()

        assert course.is_active is True
        assert course.description is None


class TestProjectModel:
    """Project model."""

    def test_create_project(self, db_session):
        teacher_role = Role.query.filter_by(name='teacher').first()
        teacher = User(username='proj_teacher', real_name='T',
                       role_id=teacher_role.id)
        db_session.add(teacher)

        course = Course(name='Project Course', teacher_id=teacher.id)
        db_session.add(course)
        db_session.flush()

        project = Project(
            name='E-commerce Platform',
            description='A full-stack e-commerce site',
            course_id=course.id,
            leader_id=teacher.id,
            status='in_progress',
            tech_stack='Flask, MySQL, Bootstrap',
        )
        db_session.add(project)
        db_session.flush()

        assert project.id is not None
        assert project.course.id == course.id
        assert project.leader_id == teacher.id
        assert project.status == 'in_progress'
        assert project.teams.count() == 0
        assert project.tasks.count() == 0

    def test_project_default_status(self, db_session):
        course = Course(name='Default Proj Course')
        db_session.add(course)
        db_session.flush()
        project = Project(name='Default Status Proj', course_id=course.id)
        db_session.add(project)
        db_session.flush()
        assert project.status == 'not_started'


class TestTeamAndMemberModel:
    """Team and TeamMember models."""

    def test_create_team(self, db_session):
        from conftest import create_test_course, create_test_project
        course = create_test_course(db_session, 'TeamCourse')
        project = create_test_project(db_session, course, 'TeamProj')

        team = Team(name='Squad A', project_id=project.id,
                    description='Frontend team')
        db_session.add(team)
        db_session.flush()

        assert team.id is not None
        assert team.project.id == project.id

    def test_create_team_member(self, db_session):
        from conftest import create_test_team, create_test_user
        team = create_test_team(db_session)
        user = create_test_user(db_session)

        member = TeamMember(team_id=team.id, user_id=user.id,
                            role_in_team='backend')
        db_session.add(member)
        db_session.flush()

        assert member.id is not None
        assert member.team.id == team.id
        assert member.member.id == user.id
        assert member.role_in_team == 'backend'
        assert user in team.members.all()
        assert team in user.team_memberships.first().team

    def test_unique_team_member_constraint(self, db_session):
        from conftest import create_test_team, create_test_user
        team = create_test_team(db_session)
        user = create_test_user(db_session)

        db_session.add(TeamMember(team_id=team.id, user_id=user.id, role_in_team='frontend'))
        db_session.flush()

        dup = TeamMember(team_id=team.id, user_id=user.id, role_in_team='backend')
        db_session.add(dup)
        with pytest.raises(Exception, match='duplicate|Duplicate|UNIQUE|1062'):
            db_session.flush()


class TestTaskModel:
    """Task model."""

    def test_create_task(self, db_session):
        from conftest import create_test_project, create_test_user
        project = create_test_project(db_session, name='TaskProj')
        user = create_test_user(db_session)

        task = Task(
            project_id=project.id,
            title='Implement user login',
            description='Add JWT-based login endpoint',
            assignee_id=user.id,
            priority='high',
            status='todo',
            estimated_hours=8.0,
        )
        db_session.add(task)
        db_session.flush()

        assert task.id is not None
        assert task.project.id == project.id
        assert task.assignee.id == user.id
        assert task.priority == 'high'
        assert task.status == 'todo'

    def test_task_defaults(self, db_session):
        from conftest import create_test_project
        project = create_test_project(db_session, name='TaskDefaults')
        task = Task(project_id=project.id, title='Default task')
        db_session.add(task)
        db_session.flush()

        assert task.status == 'todo'
        assert task.priority == 'medium'
        assert float(task.estimated_hours) == 0

    def test_task_team_association(self, db_session):
        from conftest import create_test_project, create_test_team
        project = create_test_project(db_session, name='TaskTeamProj')
        team = create_test_team(db_session, project, 'TaskTeam')
        task = Task(project_id=project.id, team_id=team.id,
                    title='Team task')
        db_session.add(task)
        db_session.flush()

        assert task.team.id == team.id

    def test_task_status_transition(self, db_session):
        from conftest import create_test_project
        project = create_test_project(db_session, name='StatusProj')
        task = Task(project_id=project.id, title='Status task',
                    status='todo')
        db_session.add(task)
        db_session.flush()

        task.status = 'in_progress'
        db_session.flush()
        assert task.status == 'in_progress'

        task.status = 'done'
        db_session.flush()
        assert task.status == 'done'


class TestDailyReportModel:
    """DailyReport model."""

    def test_create_daily_report(self, db_session):
        from conftest import create_test_user, create_test_team
        user = create_test_user(db_session)
        team = create_test_team(db_session)

        report = DailyReport(
            user_id=user.id,
            team_id=team.id,
            report_date=date(2026, 6, 1),
            completed_content='Finished login page',
            problems_encountered='CSRF token issue',
            ai_tools_used='Claude Code',
            code_commits='3 commits',
            next_day_plan='Start dashboard',
            self_score=4,
        )
        db_session.add(report)
        db_session.flush()

        assert report.id is not None
        assert report.user.id == user.id
        assert report.team.id == team.id
        assert report.report_date == date(2026, 6, 1)
        assert report.is_excellent is False

    def test_duplicate_report_date_raises(self, db_session):
        from conftest import create_test_user
        user = create_test_user(db_session)

        r1 = DailyReport(user_id=user.id, report_date=date(2026, 6, 2),
                         completed_content='Work done')
        db_session.add(r1)
        db_session.flush()

        r2 = DailyReport(user_id=user.id, report_date=date(2026, 6, 2),
                         completed_content='More work')
        db_session.add(r2)
        with pytest.raises(Exception, match='duplicate|Duplicate|UNIQUE|1062'):
            db_session.flush()


class TestBugModel:
    """Bug model."""

    def test_create_bug(self, db_session):
        from conftest import create_test_user
        reporter = create_test_user(db_session, username='bug_reporter')
        assignee = create_test_user(db_session, username='bug_fixer')

        bug = Bug(
            title='Login button not working',
            description='Clicking login does nothing',
            repro_steps='1. Go to /login 2. Enter credentials 3. Click',
            expected_result='User should be redirected',
            actual_result='Nothing happens',
            severity='major',
            reporter_id=reporter.id,
            assignee_id=assignee.id,
            module='auth',
        )
        db_session.add(bug)
        db_session.flush()

        assert bug.id is not None
        assert bug.reporter.id == reporter.id
        assert bug.assignee.id == assignee.id
        assert bug.status == 'new'
        assert bug.severity == 'major'

    def test_bug_status_transition(self, db_session):
        from conftest import create_test_user
        user = create_test_user(db_session)
        bug = Bug(title='Transition test', reporter_id=user.id)
        db_session.add(bug)
        db_session.flush()

        assert bug.status == 'new'
        bug.status = 'confirmed'
        db_session.flush()
        assert bug.status == 'confirmed'

        bug.status = 'fixing'
        db_session.flush()
        assert bug.status == 'fixing'

        bug.status = 'fixed'
        db_session.flush()
        assert bug.status == 'fixed'


class TestAiRecordModel:
    """AiRecord model."""

    def test_create_ai_record(self, db_session):
        from conftest import create_test_user, create_test_project
        user = create_test_user(db_session)
        project = create_test_project(db_session, name='AI Proj')

        task = Task(project_id=project.id, title='AI task', assignee_id=user.id)
        db_session.add(task)
        db_session.flush()

        record = AiRecord(
            user_id=user.id,
            task_id=task.id,
            tool_name='Claude Code',
            scene='Generate Flask route',
            scene_category='flask_route',
            prompt_text='Create a login route',
            ai_output_summary='Generated login route with session management',
            is_adopted=True,
            has_modified=False,
            effect_description='Reduced development time',
        )
        db_session.add(record)
        db_session.flush()

        assert record.id is not None
        assert record.user.id == user.id
        assert record.task.id == task.id
        assert record.tool_name == 'Claude Code'
        assert record.is_adopted is True
        assert record.has_modified is False


class TestCrawlerConfigModel:
    """CrawlerConfig model."""

    def test_create_crawler_config(self, db_session):
        from conftest import create_test_user
        user = create_test_user(db_session)
        config = CrawlerConfig(
            name='Tech News Crawler',
            source_url='https://example.com/rss',
            source_type='tech_article',
            keywords='python, flask, AI',
            cron_expr='0 6 * * *',
            created_by=user.id,
        )
        db_session.add(config)
        db_session.flush()

        assert config.id is not None
        assert config.creator.id == user.id
        assert config.is_active is True
        assert config.request_interval == 3


class TestCrawlerDataModel:
    """CrawlerData model."""

    def test_create_crawler_data(self, db_session):
        config = CrawlerConfig(
            name='Test Config', source_url='https://example.com',
        )
        db_session.add(config)
        db_session.flush()

        data = CrawlerData(
            config_id=config.id,
            title='Python 3.12 Released',
            url='https://example.com/article',
            summary='Major new features...',
            source_type='tech_article',
            data_hash='abc123hash',
        )
        db_session.add(data)
        db_session.flush()

        assert data.id is not None
        assert data.config.id == config.id
        assert data.data_hash == 'abc123hash'


class TestModelRelationships:
    """Cross-entity relationship navigation."""

    def test_course_project_team_chain(self, db_session):
        from conftest import create_test_project, create_test_team
        project = create_test_project(db_session, name='ChainProj')

        # Add teams via relationship
        team_a = Team(name='Team A', project_id=project.id)
        team_b = Team(name='Team B', project_id=project.id)
        db_session.add_all([team_a, team_b])
        db_session.flush()

        # Navigate: project -> teams
        assert project.teams.count() == 2
        team_names = {t.name for t in project.teams.all()}
        assert team_names == {'Team A', 'Team B'}

        # Navigate: team -> project
        assert team_a.project.id == project.id

    def test_user_task_assignment(self, db_session):
        from conftest import create_test_project, create_test_user
        project = create_test_project(db_session, name='AssignProj')
        user = create_test_user(db_session, username='assignee')

        t1 = Task(project_id=project.id, title='Task 1', assignee_id=user.id)
        t2 = Task(project_id=project.id, title='Task 2', assignee_id=user.id)
        db_session.add_all([t1, t2])
        db_session.flush()

        assert user.assigned_tasks.count() == 2

    def test_bug_reporter_and_assignee(self, db_session):
        from conftest import create_test_user
        reporter = create_test_user(db_session, username='rep')
        assignee = create_test_user(db_session, username='assg')

        bug = Bug(title='Bug rel test', reporter_id=reporter.id,
                  assignee_id=assignee.id)
        db_session.add(bug)
        db_session.flush()

        assert bug.reporter.id == reporter.id
        assert bug.assignee.id == assignee.id
        assert reporter.reported_bugs.count() == 1
        assert assignee.assigned_bugs.count() == 1

    def test_user_daily_reports(self, db_session):
        from conftest import create_test_user
        user = create_test_user(db_session)

        dr1 = DailyReport(user_id=user.id, report_date=date(2026, 6, 10),
                          completed_content='A')
        dr2 = DailyReport(user_id=user.id, report_date=date(2026, 6, 11),
                          completed_content='B')
        db_session.add_all([dr1, dr2])
        db_session.flush()

        assert user.daily_reports.count() == 2

    def test_user_ai_records(self, db_session):
        from conftest import create_test_user
        user = create_test_user(db_session)

        ar1 = AiRecord(user_id=user.id, tool_name='Claude',
                       scene='test', prompt_text='x')
        ar2 = AiRecord(user_id=user.id, tool_name='ChatGPT',
                       scene='test', prompt_text='y')
        db_session.add_all([ar1, ar2])
        db_session.flush()

        assert user.ai_records.count() == 2
