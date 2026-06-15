"""Deletion and cascade behaviour tests.

Validates that foreign-key ``ondelete`` rules in ``app/models.py``
are applied correctly by the database engine.
"""

import pytest
from app.extensions import db
from app.models import (
    Course, Project, Team, TeamMember, Task, DailyReport,
    Bug, AiRecord, User, Role,
)
from conftest import tag


class TestDeleteProjectCascade:

    def test_delete_project_cascades_to_teams(self, db_session):
        """Deleting a Project removes its teams (CASCADE on Team.project_id)."""
        role_teacher = Role.query.filter_by(name='teacher').first()
        teacher = User(username=tag('DelProjTeacher'), real_name='T',
                       role_id=role_teacher.id)
        db_session.add(teacher)
        course = Course(name=tag('DelCourse'), teacher_id=teacher.id)
        db_session.add(course)
        db_session.flush()

        project = Project(name=tag('DelProjCascade'), course_id=course.id)
        db_session.add(project)
        db_session.flush()
        pid = project.id

        team_a = Team(name='Team A', project_id=pid)
        team_b = Team(name='Team B', project_id=pid)
        db_session.add_all([team_a, team_b])
        db_session.flush()

        tid_a, tid_b = team_a.id, team_b.id

        # Confirm teams exist
        assert Team.query.get(tid_a) is not None
        assert Team.query.get(tid_b) is not None

        # Delete project
        db_session.delete(project)
        db_session.flush()

        # Teams should be gone (CASCADE)
        assert Team.query.get(tid_a) is None
        assert Team.query.get(tid_b) is None

    def test_delete_project_cascades_to_tasks(self, db_session):
        """Deleting a Project removes its tasks (CASCADE on Task.project_id)."""
        course = Course(name=tag('DelCourse2'))
        db_session.add(course)
        project = Project(name=tag('DelProjTasks'), course_id=course.id)
        db_session.add(project)
        db_session.flush()
        pid = project.id

        t1 = Task(project_id=pid, title='Task 1')
        t2 = Task(project_id=pid, title='Task 2')
        db_session.add_all([t1, t2])
        db_session.flush()
        tid1, tid2 = t1.id, t2.id

        assert Task.query.get(tid1) is not None
        assert Task.query.get(tid2) is not None

        db_session.delete(project)
        db_session.flush()

        assert Task.query.get(tid1) is None
        assert Task.query.get(tid2) is None

    def test_delete_project_cascades_to_team_members(self, db_session):
        """Deleting a Project cascades through Teams to TeamMembers."""
        course = Course(name=tag('DelCourse3'))
        db_session.add(course)
        project = Project(name=tag('DelProjMembers'), course_id=course.id)
        db_session.add(project)
        db_session.flush()

        team = Team(name='MemberTeam', project_id=project.id)
        db_session.add(team)
        db_session.flush()

        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelMemberUser'), real_name='M',
                    role_id=student_role.id)
        db_session.add(user)
        db_session.flush()

        member = TeamMember(team_id=team.id, user_id=user.id,
                            role_in_team='backend')
        db_session.add(member)
        db_session.flush()
        mid = member.id

        assert TeamMember.query.get(mid) is not None

        db_session.delete(project)
        db_session.flush()

        assert TeamMember.query.get(mid) is None

    def test_delete_project_sets_leader_null(self, db_session):
        """Deleting a Project sets leader_id to NULL (SET NULL)."""
        role_teacher = Role.query.filter_by(name='teacher').first()
        teacher = User(username=tag('DelProjLeader'), real_name='L',
                       role_id=role_teacher.id)
        db_session.add(teacher)
        course = Course(name=tag('DelCourse4'))
        db_session.add(course)
        db_session.flush()

        project = Project(name=tag('DelProjLeaderTest'), course_id=course.id,
                          leader_id=teacher.id)
        db_session.add(project)
        db_session.flush()
        pid = project.id

        db_session.delete(project)
        db_session.flush()

        # Teacher should still exist
        assert User.query.get(teacher.id) is not None


class TestDeleteBugCascade:

    def test_delete_bug_sets_null_on_related_task(self, db_session):
        """Deleting a Bug sets related_bug_id to NULL on linked tasks (SET NULL)."""
        course = Course(name=tag('DelBugCourse'))
        db_session.add(course)
        project = Project(name=tag('DelBugProj'), course_id=course.id)
        db_session.add(project)
        db_session.flush()

        student_role = Role.query.filter_by(name='student').first()
        reporter = User(username=tag('DelBugRep'), real_name='BR',
                        role_id=student_role.id)
        db_session.add(reporter)
        db_session.flush()

        bug = Bug(title='Related Bug', reporter_id=reporter.id)
        db_session.add(bug)
        db_session.flush()
        bid = bug.id

        task = Task(project_id=project.id, title='Linked Task',
                    related_bug_id=bid)
        db_session.add(task)
        db_session.flush()
        tid = task.id

        # Verify the link
        assert task.related_bug_id == bid
        assert Task.query.get(tid).related_bug_id == bid

        # Delete the bug
        db_session.delete(bug)
        db_session.flush()

        # Task should survive, but related_bug_id should be NULL
        task = Task.query.get(tid)
        assert task is not None
        assert task.related_bug_id is None

        # Bug is gone
        assert Bug.query.get(bid) is None

    def test_bug_deletion_does_not_delete_reporter(self, db_session):
        """Deleting a Bug does not cascade to the reporter user."""
        student_role = Role.query.filter_by(name='student').first()
        reporter = User(username=tag('DelBugRep2'), real_name='BR2',
                        role_id=student_role.id)
        db_session.add(reporter)
        db_session.flush()
        uid = reporter.id

        bug = Bug(title='Bug with reporter', reporter_id=uid)
        db_session.add(bug)
        db_session.flush()
        bid = bug.id

        db_session.delete(bug)
        db_session.flush()

        # Reporter should still exist
        assert User.query.get(uid) is not None

    def test_delete_bug_no_effect_on_unrelated_tasks(self, db_session):
        """Deleting a Bug does not affect tasks with different related_bug_id."""
        course = Course(name=tag('DelBugCourse2'))
        db_session.add(course)
        project = Project(name=tag('DelBugProj2'), course_id=course.id)
        db_session.add(project)
        db_session.flush()

        student_role = Role.query.filter_by(name='student').first()
        reporter = User(username=tag('DelBugRep3'), real_name='BR3',
                        role_id=student_role.id)
        db_session.add(reporter)
        db_session.flush()

        bug = Bug(title='Bug to delete', reporter_id=reporter.id)
        db_session.add(bug)
        db_session.flush()
        bid = bug.id

        # Unrelated task (no related_bug_id)
        task = Task(project_id=project.id, title='Unrelated Task')
        db_session.add(task)
        db_session.flush()
        tid = task.id

        db_session.delete(bug)
        db_session.flush()

        assert Task.query.get(tid) is not None


class TestDeleteUserCascade:

    def test_delete_user_cascades_to_daily_reports(self, db_session):
        """Deleting a User cascades to their DailyReport (CASCADE)."""
        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelUserRep'), real_name='UR',
                    role_id=student_role.id)
        db_session.add(user)
        db_session.flush()
        uid = user.id

        from datetime import date
        report = DailyReport(user_id=uid, report_date=date(2026, 6, 1),
                             completed_content='Test report')
        db_session.add(report)
        db_session.flush()
        rid = report.id

        assert DailyReport.query.get(rid) is not None

        db_session.delete(user)
        db_session.flush()

        # Report should be cascade-deleted
        assert DailyReport.query.get(rid) is None

    def test_delete_user_cascades_to_ai_records(self, db_session):
        """Deleting a User cascades to their AiRecord (CASCADE)."""
        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelUserAI'), real_name='UA',
                    role_id=student_role.id)
        db_session.add(user)
        db_session.flush()
        uid = user.id

        record = AiRecord(user_id=uid, tool_name='Claude',
                          scene='test', prompt_text='x')
        db_session.add(record)
        db_session.flush()
        arid = record.id

        assert AiRecord.query.get(arid) is not None

        db_session.delete(user)
        db_session.flush()

        assert AiRecord.query.get(arid) is None

    def test_delete_user_sets_task_assignee_null(self, db_session):
        """Deleting a User sets Task.assignee_id to NULL (SET NULL)."""
        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelUserTask'), real_name='UT',
                    role_id=student_role.id)
        db_session.add(user)
        course = Course(name=tag('DelCourse5'))
        db_session.add(course)
        project = Project(name=tag('DelProj5'), course_id=course.id)
        db_session.add(project)
        db_session.flush()
        uid = user.id
        pid = project.id

        task = Task(project_id=pid, title='Assigned Task', assignee_id=uid)
        db_session.add(task)
        db_session.flush()
        tid = task.id

        assert task.assignee_id == uid

        db_session.delete(user)
        db_session.flush()

        task = Task.query.get(tid)
        assert task is not None
        assert task.assignee_id is None

    def test_delete_user_sets_course_teacher_null(self, db_session):
        """Deleting a User sets Course.teacher_id to NULL (SET NULL)."""
        teacher_role = Role.query.filter_by(name='teacher').first()
        teacher = User(username=tag('DelTeacher'), real_name='DT',
                       role_id=teacher_role.id)
        db_session.add(teacher)
        db_session.flush()
        uid = teacher.id

        course = Course(name=tag('DelCourse6'), teacher_id=uid)
        db_session.add(course)
        db_session.flush()
        cid = course.id

        assert course.teacher_id == uid

        db_session.delete(teacher)
        db_session.flush()

        course = Course.query.get(cid)
        assert course is not None
        assert course.teacher_id is None

    def test_delete_user_preserves_login_logs_if_cascaded(self, db_session):
        """Deleting a User cascades to their LoginLog (CASCADE)."""
        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelUserLog'), real_name='UL',
                    role_id=student_role.id)
        db_session.add(user)
        db_session.flush()
        uid = user.id

        from app.models import LoginLog
        log = LoginLog(user_id=uid, is_success=True)
        db_session.add(log)
        db_session.flush()
        lid = log.id

        db_session.delete(user)
        db_session.flush()

        assert LoginLog.query.get(lid) is None


class TestDeleteTeamCascade:

    def test_delete_team_cascades_to_members(self, db_session):
        """Deleting a Team cascades to its TeamMember records."""
        course = Course(name=tag('DelCourse7'))
        db_session.add(course)
        project = Project(name=tag('DelProj7'), course_id=course.id)
        db_session.add(project)
        team = Team(name='DelTeam', project_id=project.id)
        db_session.add(team)
        db_session.flush()

        student_role = Role.query.filter_by(name='student').first()
        user = User(username=tag('DelTeamMember'), real_name='TM',
                    role_id=student_role.id)
        db_session.add(user)
        db_session.flush()

        member = TeamMember(team_id=team.id, user_id=user.id)
        db_session.add(member)
        db_session.flush()
        mid = member.id

        db_session.delete(team)
        db_session.flush()

        assert TeamMember.query.get(mid) is None
        # User should still exist
        assert User.query.get(user.id) is not None

    def test_delete_team_sets_task_team_null(self, db_session):
        """Deleting a Team sets Task.team_id to NULL (SET NULL)."""
        course = Course(name=tag('DelCourse8'))
        db_session.add(course)
        project = Project(name=tag('DelProj8'), course_id=course.id)
        db_session.add(project)
        team = Team(name='DelTeam2', project_id=project.id)
        db_session.add(team)
        db_session.flush()
        tid_team = team.id

        task = Task(project_id=project.id, title='Team Task',
                    team_id=tid_team)
        db_session.add(task)
        db_session.flush()
        tid_task = task.id

        assert task.team_id == tid_team

        db_session.delete(team)
        db_session.flush()

        task = Task.query.get(tid_task)
        assert task is not None
        assert task.team_id is None
