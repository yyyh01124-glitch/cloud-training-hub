import logging; logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
from app import create_app
app = create_app('development')
with app.app_context():
    with app.test_client() as c:
        r = c.post('/auth/login', data={'username': 'student1', 'password': '123456'}, follow_redirects=True)
        print(f'Status: {r.status_code}')
        h = r.data.decode('utf-8', errors='replace')
        if 'Traceback' in h or 'AttributeError' in h or 'Error' in h:
            print('HAS ERROR')
        elif 'Cloud' in h or 'dashboard' in h.lower():
            print('LOGIN OK')
        else:
            print('UNKNOWN')
