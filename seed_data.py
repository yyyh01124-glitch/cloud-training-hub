"""Seed demo data - teachers, students, courses, projects, teams, tasks, reports, bugs, AI records, crawler data."""
import os, sys, random
from datetime import date, timedelta

os.environ['FLASK_CONFIG'] = 'development'
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:123456@localhost:3306/cloud_training_hub'
os.environ['SECRET_KEY'] = 'seed'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import create_app
from app.extensions import db
from app.models import *

app = create_app()

with app.app_context():
    print("Clearing old test data...")
    # Clean existing test data (keep admin)
    AiRecord.query.delete()
    DailyReport.query.delete()
    Bug.query.delete()
    Task.query.delete()
    CrawlerData.query.delete()
    CrawlerConfig.query.delete()
    TeamMember.query.delete()
    Team.query.delete()
    Score.query.delete()
    Project.query.delete()
    Course.query.delete()
    User.query.filter(User.username != 'admin').delete()
    db.session.commit()
    print("Old data cleared.\n")

    # ---- Users ----
    print("Creating users...")
    teachers = []
    for i, name in enumerate(['张老师', '李老师'], 1):
        u = User(username=f'teacher{i}', real_name=name, role_id=2, email=f'teacher{i}@cloudhub.com')
        u.set_password('123456')
        db.session.add(u)
        db.session.flush()
        teachers.append(u)

    students_data = [
        ('赵一', 'leader'), ('钱二', 'backend'), ('孙三', 'frontend'),
        ('周四', 'database'), ('吴五', 'devops'),
        ('郑六', 'leader'), ('王七', 'backend'), ('冯八', 'frontend'),
        ('陈九', 'database'), ('褚十', 'devops'),
    ]
    students = []
    for i, (name, _) in enumerate(students_data, 1):
        u = User(username=f'student{i}', real_name=name, role_id=3)
        u.set_password('123456')
        db.session.add(u)
        db.session.flush()
        students.append(u)
    db.session.commit()
    print(f"  {len(teachers)} teachers, {len(students)} students created")

    # ---- Courses ----
    print("Creating courses...")
    c1 = Course(name='云计算应用开发实训', description='基于云计算技术的应用开发综合实训，涵盖Python Web、Docker、爬虫等技术',
                teacher_id=teachers[0].id, start_date=date(2026, 3, 1), end_date=date(2026, 7, 15), is_active=True)
    c2 = Course(name='Python Web项目实训', description='使用Flask框架完成企业级Web应用开发，包含前后端分离和容器化部署',
                teacher_id=teachers[1].id, start_date=date(2026, 3, 15), end_date=date(2026, 7, 30), is_active=True)
    db.session.add_all([c1, c2])
    db.session.commit()
    print(f"  2 courses created")

    # ---- Projects ----
    print("Creating projects...")
    p1 = Project(course_id=c1.id, name='云智实训管理平台', description='高校云计算实训全流程管理平台', leader_id=teachers[0].id,
                 start_date=date(2026, 3, 1), end_date=date(2026, 6, 30), status='in_progress',
                 tech_stack='Python,Flask,MySQL,Docker,Nginx', deploy_url='http://8.146.230.215', git_repo_url='https://github.com/demo/cloud-training-hub')
    p2 = Project(course_id=c1.id, name='校园二手交易平台', description='校内二手物品交易与信息发布平台', leader_id=teachers[0].id,
                 start_date=date(2026, 3, 20), end_date=date(2026, 6, 20), status='in_progress',
                 tech_stack='Python,Flask,Vue3,MySQL,Redis')
    p3 = Project(course_id=c2.id, name='招聘信息采集分析平台', description='自动采集招聘网站岗位信息并分析展示', leader_id=teachers[1].id,
                 start_date=date(2026, 4, 1), end_date=date(2026, 7, 1), status='not_started',
                 tech_stack='Python,Scrapy,Flask,ECharts,MySQL')
    db.session.add_all([p1, p2, p3])
    db.session.commit()
    print(f"  3 projects created")

    # ---- Teams ----
    print("Creating teams...")
    teams_data = [
        (p1.id, '凌云组', students[0].id, '追求卓越，勇攀高峰'),
        (p1.id, '码力全开组', students[5].id, '代码改变世界'),
        (p2.id, '极客先锋组', None, '技术驱动创新'),
    ]
    teams_list = []
    for pid, name, lid, desc in teams_data:
        t = Team(project_id=pid, name=name, leader_id=lid, description=desc)
        db.session.add(t)
        db.session.flush()
        teams_list.append(t)
    db.session.commit()
    print(f"  {len(teams_list)} teams created")

    # ---- Team Members ----
    print("Adding team members...")
    member_roles = ['leader', 'backend', 'frontend', 'database', 'devops']
    # Team 1 (5 members)
    for i in range(5):
        db.session.add(TeamMember(team_id=teams_list[0].id, user_id=students[i].id, role_in_team=member_roles[i]))
    # Team 2 (5 members)
    for i in range(5, 10):
        db.session.add(TeamMember(team_id=teams_list[1].id, user_id=students[i].id, role_in_team=member_roles[i - 5]))
    # Team 3 (2 members - partial)
    db.session.add(TeamMember(team_id=teams_list[2].id, user_id=students[0].id, role_in_team='leader'))
    db.session.add(TeamMember(team_id=teams_list[2].id, user_id=students[1].id, role_in_team='backend'))
    db.session.commit()
    print(f"  12 team members added")

    # ---- Tasks ----
    print("Creating tasks...")
    tasks_data = [
        # Task board demo: different statuses
        (p1.id, teams_list[0].id, '需求分析与ER图设计', students[0].id, 'todo', 'high', 4, date(2026, 3, 20)),
        (p1.id, teams_list[0].id, 'Flask项目骨架搭建', students[1].id, 'in_progress', 'high', 8, date(2026, 3, 25)),
        (p1.id, teams_list[0].id, '用户登录注册功能', students[1].id, 'to_test', 'high', 6, date(2026, 3, 28)),
        (p1.id, teams_list[0].id, 'Bootstrap页面布局', students[2].id, 'done', 'medium', 4, date(2026, 3, 18)),
        (p1.id, teams_list[0].id, '数据库建表脚本', students[3].id, 'done', 'high', 3, date(2026, 3, 16)),
        (p1.id, teams_list[0].id, 'Docker基础配置', students[4].id, 'delayed', 'medium', 6, date(2026, 3, 15)),
        (p1.id, teams_list[0].id, '性能优化调研', students[4].id, 'closed', 'low', 2, date(2026, 3, 10)),

        (p1.id, teams_list[1].id, '任务看板模块开发', students[5].id, 'in_progress', 'high', 8, date(2026, 3, 30)),
        (p1.id, teams_list[1].id, '日报模块开发', students[6].id, 'todo', 'high', 6, date(2026, 4, 5)),
        (p1.id, teams_list[1].id, 'Bug管理模块UI', students[7].id, 'done', 'medium', 5, date(2026, 3, 22)),
    ]
    for (project_id, team_id, title, assignee_id, status, priority, hours, due) in tasks_data:
        db.session.add(Task(
            project_id=project_id, team_id=team_id, title=title,
            assignee_id=assignee_id, status=status, priority=priority,
            estimated_hours=hours, due_date=due,
            start_date=due - timedelta(days=7),
            description=f'{title}的详细需求文档见飞书共享文档。需要完成前后端联调并通过测试。',
            completion_note='已完成并通过代码审查' if status == 'done' else ('延期至下个迭代' if status == 'delayed' else None)
        ))
    db.session.commit()
    print(f"  {len(tasks_data)} tasks created across all statuses")

    # ---- Daily Reports ----
    print("Creating daily reports...")
    today = date.today()
    for i, s in enumerate(students):
        for days_ago in range(random.randint(1, 4)):
            rd = today - timedelta(days=days_ago)
            existing = DailyReport.query.filter_by(user_id=s.id, report_date=rd).first()
            if existing:
                continue
            contents = [
                '完成了数据库表结构设计，确认了外键关系',
                'Flask蓝图结构搭建完成，路由模块化拆分',
                '任务看板前端页面完成，实现了拖拽功能',
                '调试了登录接口，修复了cookie过期问题',
                '开始写爬虫模块，用requests+BS4解析页面',
            ]
            db.session.add(DailyReport(
                user_id=s.id, team_id=teams_list[i // 5].id if i < 10 and i // 5 < len(teams_list) else None,
                report_date=rd,
                completed_content=random.choice(contents),
                problems_encountered='数据库连接池偶尔超时' if random.random() > 0.5 else '页面样式兼容性问题',
                ai_tools_used='通义灵码, 豆包',
                ai_help_summary='帮助生成了部分Flask路由代码和SQL查询',
                code_commits=f'commit {random.randint(100000, 999999)} - feat: add feature',
                next_day_plan='继续完成剩余模块开发',
                self_score=random.randint(3, 5)
            ))
    db.session.commit()
    report_count = DailyReport.query.count()
    print(f"  {report_count} daily reports created")

    # ---- Bugs ----
    print("Creating bugs...")
    bug_severities = ['fatal', 'major', 'normal', 'minor', 'suggestion']
    bug_statuses = ['new', 'confirmed', 'fixing', 'fixed', 'closed']
    bug_modules = ['登录模块', '任务看板', '日报模块', '项目中心', '小组管理', '爬虫模块']

    bugs_data = [
        ('登录后首次加载白屏', 'fatal', 'closed', students[0].id, students[1].id, '登录模块',
         '原因是前端JS加载顺序错误，调整后解决'),
        ('任务拖拽后状态不同步', 'major', 'fixed', students[5].id, students[6].id, '任务看板',
         'AJAX请求未携带CSRF token，添加后修复'),
        ('日报提交后页面不刷新', 'normal', 'fixing', students[9].id, students[7].id, '日报模块', None),
        ('密码修改后session未更新', 'major', 'confirmed', students[1].id, students[1].id, '登录模块', None),
        ('IE浏览器样式错乱', 'minor', 'new', students[2].id, students[2].id, '项目中心', None),
        ('建议增加数据导出功能', 'suggestion', 'new', students[3].id, students[4].id, '项目中心', None),
        ('爬虫定时任务未启动', 'normal', 'new', students[8].id, students[8].id, '爬虫模块', None),
    ]
    for (title, severity, status, reporter_id, assignee_id, module, solution) in bugs_data:
        b = Bug(title=title, severity=severity, status=status, reporter_id=reporter_id,
                assignee_id=assignee_id, module=module, solution=solution,
                description=f'详细描述：{title}的具体表现',
                repro_steps='1. 打开系统 2. 执行操作 3. 观察异常', expected_result='正常显示', actual_result='出现异常')
        if status == 'closed':
            b.closed_at = today
        db.session.add(b)
    db.session.commit()
    print(f"  {len(bugs_data)} bugs created across all statuses")

    # ---- AI Records ----
    print("Creating AI records...")
    ai_data = [
        (students[0].id, '通义灵码', 'db_design', '帮我生成16张表的建表SQL', '生成了完整DDL，修改了外键约束部分', True, True),
        (students[1].id, '豆包', 'flask_route', '帮我写Flask用户登录路由', '基本可用，修改了密码验证逻辑', True, True),
        (students[2].id, '通义灵码', 'style_optimize', '优化看板页面的CSS布局', '生成了grid布局，调整了响应式', True, True),
        (students[3].id, 'ChatGPT', 'error_explain', 'SQLAlchemy报错IntegrityError原因', '解释了外键约束冲突问题', True, False),
        (students[4].id, '通义灵码', 'dockerfile', '生成多阶段构建Dockerfile', '生成了optimized版本，直接采用', True, False),
        (students[5].id, '豆包', 'test_case', '生成任务模块的测试用例', '生成了20条用例，补充了边界测试', True, True),
        (students[6].id, '通义灵码', 'deploy_doc', '生成阿里云部署文档大纲', '基本框架可用，补充了ECS配置步骤', True, True),
        (students[7].id, 'ChatGPT', 'log_analysis', '分析nginx错误日志', '定位到了502错误原因', True, False),
        (students[8].id, '豆包', 'compose', '编写docker-compose.yml', '生成了web+mysql+nginx三服务配置', True, True),
        (students[9].id, '通义灵码', 'project_summary', '帮我写实训总结报告大纲', '生成了完整大纲，补充了个人体会', True, True),
    ]
    for (user_id, tool, scene, prompt, summary, adopted, modified) in ai_data:
        db.session.add(AiRecord(
            user_id=user_id, tool_name=tool, scene_category=scene,
            scene=f'使用{tool}进行{scene}相关开发',
            prompt_text=prompt, ai_output_summary=summary,
            is_adopted=adopted, has_modified=modified,
            modification_note='修改了部分实现逻辑' if modified else '',
            effect_description=f'节省了约{random.randint(30, 90)}分钟开发时间',
            related_files=f'app/routes/{scene.split("_")[0]}.py',
            risk_note='需要人工审查代码安全性' if random.random() > 0.5 else '使用正常无风险'
        ))
    db.session.commit()
    print(f"  {len(ai_data)} AI records created")

    # ---- Crawler ----
    print("Creating crawler configs...")
    cfg = CrawlerConfig(
        name='GitHub Python Trending',
        source_url='https://github.com/trending/python?since=daily',
        source_type='opensource', keywords='flask,docker,ai,agent',
        request_interval=5, created_by=teachers[0].id
    )
    db.session.add(cfg)
    db.session.flush()

    # Add some sample crawled data
    sample_data = [
        ('fastapi/fastapi', 'FastAPI framework, high performance', 'fastapi,python'),
        ('tiangolo/full-stack-fastapi-template', 'Full stack FastAPI template', 'fastapi,fullstack'),
        ('apache/airflow', 'Apache Airflow workflow management', 'airflow,workflow,python'),
        ('psf/black', 'Uncompromising Python code formatter', 'python,formatter'),
        ('pallets/flask', 'The Python micro framework', 'flask,python'),
    ]
    import hashlib, json
    for title, desc, keywords in sample_data:
        db.session.add(CrawlerData(
            config_id=cfg.id, title=title, summary=desc,
            url=f'https://github.com/{title.split("/")[0]}/{title.split("/")[1] if "/" in title else title}',
            source_type='opensource', keywords_matched=keywords,
            raw_data=json.dumps({'title': title, 'desc': desc, 'stars': random.randint(100, 50000)}, ensure_ascii=False),
            data_hash=hashlib.sha256(title.encode()).hexdigest()
        ))
    db.session.commit()
    total_crawler = CrawlerData.query.count()
    print(f"  1 crawler config, {total_crawler} data entries created")

    # ---- Summary ----
    print(f"\n{'='*50}")
    print("  Demo data seeding complete!")
    print(f"  {'='*50}")
    print(f"  Users:     {User.query.count()} (1 admin + {len(teachers)} teachers + {len(students)} students)")
    print(f"  Courses:   {Course.query.count()}")
    print(f"  Projects:  {Project.query.count()}")
    print(f"  Teams:     {Team.query.count()}")
    print(f"  Members:   {TeamMember.query.count()}")
    print(f"  Tasks:     {Task.query.count()}")
    print(f"  Reports:   {DailyReport.query.count()}")
    print(f"  Bugs:      {Bug.query.count()}")
    print(f"  AI Records:{AiRecord.query.count()}")
    print(f"  Crawler:   {CrawlerConfig.query.count()} configs, {CrawlerData.query.count()} entries")
    print(f"{'='*50}")
    print("\n  Login: admin/admin123")
    print("  Teacher accounts: teacher1/123456, teacher2/123456")
    print("  Student accounts: student1~student10/123456")
