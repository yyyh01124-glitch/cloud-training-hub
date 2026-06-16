import os

os.environ.setdefault('FLASK_CONFIG', 'development')
os.environ.setdefault('SECRET_KEY', 'cloud-training-hub-dev-key-2024')
os.environ.setdefault(
    'DATABASE_URL',
    'mysql+pymysql://root:123456@localhost:3306/cloud_training_hub?charset=utf8mb4'
)

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
