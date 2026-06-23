import logging; logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
from app import create_app
from app.models import User
app = create_app('development')
with app.app_context():
    with app.test_client() as c:
        c.post('/auth/login', data={'username': 'admin', 'password': '123456'})
        u = User.query.filter(User.username != 'admin').order_by(User.id.desc()).first()
        if u:
            print(f'Deleting user {u.id} ({u.username})...')
            r = c.post(f'/admin/users/{u.id}/delete', follow_redirects=True)
            print(f'Status: {r.status_code}')
            decoded = r.data.decode('utf-8', errors='replace')
            if 'success' in decoded.lower() or 'ok' in decoded.lower() or u'已删除' in decoded:
                print('SUCCESS: User deleted')
            elif 'fail' in decoded.lower() or u'失败' in decoded:
                print('FAILED')
            else:
                print('Check response')
