from app import create_app
app = create_app('development')
import logging
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

routes = [
    ('/', 'Dash'), ('/auth/profile', 'Profile'), ('/classes/', 'ClassList'),
    ('/classes/1', 'CDetail'), ('/classes/join', 'Join'),
    ('/admin/users', 'Users'), ('/admin/logs', 'Logs'),
    ('/admin/student/11', 'StuProf'), ('/admin/import-students', 'Import'),
    ('/projects/', 'Proj'), ('/projects/courses', 'Courses'),
    ('/projects/courses/1', 'CourseD'), ('/projects/courses/create', 'CreateC'),
    ('/projects/create', 'CreateP'), ('/projects/1', 'ProjDet'),
    ('/teams/', 'Teams'), ('/teams/1', 'TeamDet'),
    ('/tasks/board', 'Board'), ('/tasks/list', 'TList'),
    ('/tasks/overview', 'TOver'), ('/tasks/create', 'CTask'),
    ('/tasks/1', 'TDetail'), ('/reports/', 'Reports'),
    ('/reports/create', 'CReport'), ('/reports/missing', 'Miss'),
    ('/bugs/', 'Bugs'), ('/bugs/create', 'CBug'),
    ('/crawler/data', 'Crawl'), ('/ai-records/', 'AI'),
    ('/ai-records/stats', 'AIStat'), ('/scores/', 'Scores'),
    ('/announcements/', 'Ann'), ('/notifications/', 'Notif'),
]

with app.app_context():
    with app.test_client() as c:
        for user in ['admin', 'teacher1', 'student1']:
            c.get('/auth/logout')
            c.post('/auth/login', data={'username': user, 'password': '123456'})
            ok, e500 = 0, 0
            for path, _ in routes:
                r = c.get(path)
                if r.status_code == 500: e500 += 1
                else: ok += 1
            print(f'{user:10s}: {ok} OK, {e500} errors')
