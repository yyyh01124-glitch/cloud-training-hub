from flask import Flask, render_template, redirect, url_for
import bcrypt
from app.config import config_map
from app.extensions import db, login_manager, migrate


def create_app(config_name=None):
    if config_name is None:
        from os import environ
        config_name = environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # 验证 admin 密码
    with app.app_context():
        _ensure_admin_password()

    # 蓝图注册
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.projects import project_bp
    from app.routes.teams import team_bp
    from app.routes.tasks import task_bp
    from app.routes.reports import report_bp
    from app.routes.bugs import bug_bp
    from app.routes.crawler import crawler_bp
    from app.routes.ai_records import ai_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.announcements import announcement_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(announcement_bp, url_prefix='/announcements')
    app.register_blueprint(project_bp, url_prefix='/projects')
    app.register_blueprint(team_bp, url_prefix='/teams')
    app.register_blueprint(task_bp, url_prefix='/tasks')
    app.register_blueprint(report_bp, url_prefix='/reports')
    app.register_blueprint(bug_bp, url_prefix='/bugs')
    app.register_blueprint(crawler_bp, url_prefix='/crawler')
    app.register_blueprint(ai_bp, url_prefix='/ai-records')
    app.register_blueprint(dashboard_bp, url_prefix='/')

    # 错误处理
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('errors/500.html'), 500

    # 上下文注入
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        return {
            'current_user': current_user,
            'roles': {'admin': '管理员', 'teacher': '教师', 'student': '学生'},
            'task_statuses': {
                'todo': '待开始', 'in_progress': '进行中', 'to_test': '待测试',
                'done': '已完成', 'delayed': '已延期', 'closed': '已关闭'
            },
            'task_priorities': {'high': '高', 'medium': '中', 'low': '低'},
            'bug_severities': {
                'fatal': '致命', 'major': '严重', 'normal': '一般',
                'minor': '轻微', 'suggestion': '建议'
            },
            'bug_statuses': {
                'new': '新建', 'confirmed': '已确认', 'fixing': '修复中',
                'fixed': '已修复', 'closed': '已关闭', 'wontfix': '暂不处理'
            },
            'team_roles': {
                'leader': '项目经理', 'backend': '后端开发', 'frontend': '前端开发',
                'database': '数据库与爬虫', 'devops': '部署运维', 'member': '组员'
            },
            'ai_scenes': {
                'db_design': '生成数据库表结构', 'flask_route': '生成Flask路由',
                'error_explain': '解释报错', 'style_optimize': '优化页面样式',
                'test_case': '生成测试用例', 'dockerfile': '编写Dockerfile',
                'compose': '编写docker-compose', 'deploy_doc': '生成部署文档',
                'log_analysis': '分析日志', 'project_summary': '生成项目总结',
                'other': '其他'
            },
            'project_statuses': {
                'not_started': '未开始', 'in_progress': '进行中',
                'completed': '已完成', 'archived': '已归档'
            },
        }

    return app


def _ensure_admin_password():
    from app.models import User
    admin = User.query.filter_by(username='admin').first()
    if admin:
        try:
            if not bcrypt.checkpw('admin123'.encode(), admin.password_hash.encode()):
                admin.set_password('admin123')
                db.session.commit()
                import logging
                logging.getLogger(__name__).info('Admin password re-hashed')
        except ValueError:
            admin.set_password('admin123')
            db.session.commit()
