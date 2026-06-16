"""Comprehensive system test - local + ECS"""
import os, sys, json
os.environ['FLASK_CONFIG'] = 'development'
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:123456@localhost:3306/cloud_training_hub?charset=utf8mb4'
os.environ['SECRET_KEY'] = 'test'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from app.extensions import db
from app.models import *
from datetime import date

app = create_app()
P = 0; F = 0
errors = []

def t(msg, ok):
    global P, F
    if ok: P += 1; print(f"  [PASS] {msg}")
    else: F += 1; print(f"  [FAIL] {msg}"); errors.append(msg)

def test_local():
    global P, F
    print("\n" + "="*60)
    print("LOCAL COMPREHENSIVE SYSTEM TEST")
    print("="*60)

    admin = User.query.filter_by(username='admin').first()
    t("Admin exists", admin is not None)
    t("Admin name encoding correct (系统管理员, not garbled)", admin and admin.real_name == '系统管理员')

    with app.test_client() as c:
        # ===== LOGIN =====
        print("\n--- Module 1: Auth ---")
        r = c.post('/auth/login', data={'username': 'wrong', 'password': 'wrong'})
        t("Wrong password rejected (200)", r.status_code == 200)

        r = c.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        t("Login success", r.status_code == 200)

        r = c.get('/auth/profile')
        t("Profile page (200)", r.status_code == 200)

        # ===== PAGE ACCESS =====
        print("\n--- Page Access ---")
        pages = [
            ('/', 'Dashboard'),
            ('/tasks/board', 'Task Board'),
            ('/tasks/list', 'Task List'),
            ('/tasks/overview', 'Task Overview'),
            ('/projects/', 'Projects'),
            ('/projects/courses', 'Courses'),
            ('/teams/', 'Teams'),
            ('/reports/', 'Reports'),
            ('/reports/missing', 'Missing Reports'),
            ('/reports/stats', 'Report Stats'),
            ('/bugs/', 'Bugs'),
            ('/crawler/data', 'Crawler Data'),
            ('/crawler/configs', 'Crawler Configs'),
            ('/crawler/stats', 'Crawler Stats'),
            ('/ai-records/', 'AI Records'),
            ('/admin/users', 'Admin Users'),
            ('/admin/logs', 'Admin Logs'),
            ('/announcements/', 'Announcements'),
            ('/scores/', 'Scores'),
        ]
        for url, name in pages:
            r = c.get(url)
            t(f"{name} page (200)", r.status_code == 200)

        # ===== CRUD: Course =====
        print("\n--- Module 2: Course CRUD ---")
        r = c.post('/projects/courses/create', data={
            'name': 'SYS_TEST_课程', 'description': '系统测试', 'is_active': 'on'
        }, follow_redirects=True)
        course = Course.query.filter(Course.name.contains('SYS_TEST')).first()
        t("Create course", course is not None)

        r = c.get(f'/projects/courses/{course.id}')
        t("Course detail page", r.status_code == 200)

        # ===== CRUD: Project =====
        print("\n--- Module 2: Project CRUD ---")
        r = c.post('/projects/create', data={
            'course_id': str(course.id), 'name': 'SYS_TEST_项目',
            'description': '系统测试项目', 'status': 'in_progress'
        }, follow_redirects=True)
        project = Project.query.filter(Project.name.contains('SYS_TEST')).first()
        t("Create project", project is not None)

        r = c.get(f'/projects/{project.id}')
        t("Project detail page", r.status_code == 200)

        # ===== CRUD: Team =====
        print("\n--- Module 3: Team CRUD ---")
        r = c.post('/teams/create', data={
            'project_id': str(project.id), 'name': 'SYS_TEST_小组'
        }, follow_redirects=True)
        team = Team.query.filter_by(name='SYS_TEST_小组').first()
        t("Create team", team is not None)

        r = c.get(f'/teams/{team.id}')
        t("Team detail page", r.status_code == 200)

        # ===== CRUD: Task =====
        print("\n--- Module 4: Task CRUD ---")
        r = c.post('/tasks/create', data={
            'project_id': str(project.id), 'team_id': str(team.id),
            'title': 'SYS_TEST_任务1', 'priority': 'high', 'status': 'in_progress'
        }, follow_redirects=True)
        task1 = Task.query.filter_by(title='SYS_TEST_任务1').first()
        t("Create task 1", task1 is not None)

        r = c.post('/tasks/create', data={
            'project_id': str(project.id), 'title': 'SYS_TEST_任务2', 'status': 'todo'
        }, follow_redirects=True)
        task2 = Task.query.filter_by(title='SYS_TEST_任务2').first()
        t("Create task 2", task2 is not None)

        r = c.post(f'/tasks/{task1.id}/status', data={'status': 'to_test'}, follow_redirects=True)
        updated = db.session.get(Task, task1.id)
        t(f"Task status flow: {updated.status}", updated.status == 'to_test')

        r = c.get(f'/tasks/{task1.id}')
        t("Task detail page", r.status_code == 200)

        # ===== CRUD: Daily Report =====
        print("\n--- Module 5: Daily Report ---")
        r = c.post('/reports/create', data={
            'completed_content': 'SYS_TEST_日报内容', 'self_score': '4'
        }, follow_redirects=True)
        report = DailyReport.query.filter(DailyReport.completed_content.contains('SYS_TEST')).first()
        t("Create daily report", report is not None)

        r = c.post(f'/reports/{report.id}/review', data={
            'teacher_comment': 'SYS_TEST_点评', 'is_excellent': 'on'
        }, follow_redirects=True)
        reviewed = db.session.get(DailyReport, report.id)
        t("Teacher review", reviewed.is_excellent == True)

        # ===== CRUD: Bug =====
        print("\n--- Module 6: Bug CRUD ---")
        r = c.post('/bugs/create', data={
            'title': 'SYS_TEST_Bug1', 'severity': 'major',
            'module': 'SYS_TEST', 'description': '测试Bug'
        }, follow_redirects=True)
        bug = Bug.query.filter_by(title='SYS_TEST_Bug1').first()
        t("Create bug", bug is not None)

        for status in ['confirmed', 'fixing', 'fixed', 'closed']:
            r = c.post(f'/bugs/{bug.id}/edit', data={
                'title': bug.title, 'severity': 'major', 'module': 'SYS_TEST',
                'status': status, 'solution': 'Fixed' if status == 'fixed' else ''
            }, follow_redirects=True)
            b = db.session.get(Bug, bug.id)
            t(f"Bug status: {b.status}", b.status == status)

        # ===== CRUD: AI Record =====
        print("\n--- Module 8: AI Record ---")
        r = c.post('/ai-records/create', data={
            'tool_name': 'SYS_TEST_Tool', 'scene': '测试场景',
            'scene_category': 'other', 'prompt_text': '测试提示词'
        }, follow_redirects=True)
        ai = AiRecord.query.filter_by(tool_name='SYS_TEST_Tool').first()
        t("Create AI record", ai is not None)

        # ===== Crawler =====
        print("\n--- Module 7: Crawler ---")
        r = c.post('/crawler/configs/create', data={
            'name': 'SYS_TEST_Crawler', 'source_url': 'https://example.com',
            'source_type': 'tech_article', 'request_interval': '5'
        }, follow_redirects=True)
        cfg = CrawlerConfig.query.filter_by(name='SYS_TEST_Crawler').first()
        t("Create crawler config", cfg is not None)

        # ===== Announcement =====
        print("\n--- Announcement ---")
        r = c.post('/announcements/create', data={
            'title': 'SYS_TEST_公告', 'content': '测试公告内容', 'is_pinned': 'on'
        }, follow_redirects=True)
        ann = Announcement.query.filter_by(title='SYS_TEST_公告').first()
        t("Create announcement", ann is not None)

        # ===== Score =====
        print("\n--- Score ---")
        r = c.post('/scores/create', data={
            'project_id': str(project.id), 'team_id': str(team.id),
            'category': 'SYS_TEST_评分', 'score': '85', 'max_score': '100'
        }, follow_redirects=True)
        score = Score.query.filter_by(category='SYS_TEST_评分').first()
        t("Create score", score is not None)

        # ===== PERMISSION =====
        print("\n--- Permission ---")
        c.get('/auth/logout')
        r = c.get('/admin/users')
        t("Unauthenticated redirected to login (302)", r.status_code == 302)

        # Student login test
        student = User.query.filter_by(username='student1').first()
        if student:
            r = c.post('/auth/login', data={'username': 'student1', 'password': '123456'}, follow_redirects=True)
            t("Student login", r.status_code == 200)

            r = c.get('/admin/users')
            t("Student blocked from admin (403)", r.status_code == 403)
            c.get('/auth/logout')

        # ===== DELETION =====
        print("\n--- Deletion Cascade ---")
        r = c.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # Delete project -> cascades team, tasks
        pid = project.id
        tid = team.id
        t1id = task1.id
        t2id = task2.id
        rid = report.id
        bid = bug.id
        aid = ai.id
        cid = course.id
        aid_ann = ann.id
        sid = score.id
        crid = cfg.id

        r = c.post(f'/projects/{pid}/delete', follow_redirects=True)
        t("Project deleted", db.session.get(Project, pid) is None)
        t("Team cascade-deleted", db.session.get(Team, tid) is None)
        t("Task1 cascade-deleted", db.session.get(Task, t1id) is None)
        t("Task2 cascade-deleted", db.session.get(Task, t2id) is None)

        # ===== CLEANUP =====
        print("\n--- Cleanup ---")
        for obj_id, obj_type in [
            (rid, 'report'), (bid, 'bug'), (aid, 'ai'),
            (cid, 'course'), (aid_ann, 'announcement'),
            (sid, 'score'), (crid, 'crawler_config')
        ]:
            if not obj_id: continue
            models = {
                'report': DailyReport, 'bug': Bug, 'ai': AiRecord,
                'course': Course, 'announcement': Announcement,
                'score': Score, 'crawler_config': CrawlerConfig
            }
            obj = db.session.get(models[obj_type], obj_id)
            if obj:
                db.session.delete(obj)
        db.session.commit()
        t("All test data cleaned", True)

    print(f"\n{'='*40}")
    print(f"LOCAL TEST: {P} passed, {F} failed")
    for e in errors[-10:]:
        print(f"  FAILED: {e}")
    print(f"{'='*40}")

if __name__ == '__main__':
    with app.app_context():
        test_local()
