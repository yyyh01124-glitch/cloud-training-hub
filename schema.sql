-- ============================================================
-- 云智实训管理平台 (Cloud Training Hub)
-- 前9个模块完整 DDL
-- MySQL 8.0
-- ============================================================

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS cloud_training_hub
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE cloud_training_hub;

-- ============================================================
-- 模块一：用户登录与权限管理
-- ============================================================

-- 角色表
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '角色名称: admin, teacher, student',
    display_name VARCHAR(100) NOT NULL COMMENT '显示名称',
    description VARCHAR(255) DEFAULT '' COMMENT '角色描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COMMENT='角色表';

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希(bcrypt)',
    real_name VARCHAR(50) NOT NULL COMMENT '真实姓名',
    email VARCHAR(100) DEFAULT '' COMMENT '邮箱',
    phone VARCHAR(20) DEFAULT '' COMMENT '手机号',
    avatar VARCHAR(255) DEFAULT '' COMMENT '头像路径',
    role_id INT NOT NULL COMMENT '角色ID',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用: 1启用 0禁用',
    login_fail_count INT DEFAULT 0 COMMENT '登录失败次数',
    last_login_at TIMESTAMP NULL COMMENT '最后登录时间',
    last_login_ip VARCHAR(45) DEFAULT '' COMMENT '最后登录IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX idx_users_role (role_id),
    INDEX idx_users_active (is_active),
    INDEX idx_users_username (username)
) ENGINE=InnoDB COMMENT='用户表';

-- 登录日志表
CREATE TABLE IF NOT EXISTS login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ip_address VARCHAR(45) DEFAULT '' COMMENT '登录IP',
    user_agent VARCHAR(500) DEFAULT '' COMMENT '浏览器UA',
    is_success TINYINT(1) DEFAULT 0 COMMENT '是否成功',
    fail_reason VARCHAR(255) DEFAULT '' COMMENT '失败原因',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_logs_user (user_id),
    INDEX idx_logs_time (created_at)
) ENGINE=InnoDB COMMENT='登录日志表';

-- ============================================================
-- 模块二：课程与实训项目管理
-- ============================================================

-- 课程表
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '课程名称',
    description TEXT COMMENT '课程简介',
    teacher_id INT COMMENT '负责教师',
    start_date DATE COMMENT '开课日期',
    end_date DATE COMMENT '结课日期',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_courses_teacher (teacher_id)
) ENGINE=InnoDB COMMENT='课程表';

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_id INT NOT NULL COMMENT '所属课程',
    name VARCHAR(200) NOT NULL COMMENT '项目名称',
    description TEXT COMMENT '项目简介',
    start_date DATE COMMENT '开始时间',
    end_date DATE COMMENT '结束时间',
    leader_id INT COMMENT '项目负责人',
    status ENUM('not_started','in_progress','completed','archived') DEFAULT 'not_started' COMMENT '项目状态',
    tech_stack VARCHAR(500) DEFAULT '' COMMENT '技术栈',
    score_rule TEXT COMMENT '评分规则',
    deploy_url VARCHAR(500) DEFAULT '' COMMENT '部署地址',
    git_repo_url VARCHAR(500) DEFAULT '' COMMENT 'Git仓库地址',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_projects_course (course_id),
    INDEX idx_projects_status (status)
) ENGINE=InnoDB COMMENT='项目表';

-- ============================================================
-- 模块三：小组管理
-- ============================================================

-- 小组表
CREATE TABLE IF NOT EXISTS teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '所属项目',
    name VARCHAR(100) NOT NULL COMMENT '小组名称',
    leader_id INT COMMENT '组长',
    description VARCHAR(500) DEFAULT '' COMMENT '小组简介',
    deploy_url VARCHAR(500) DEFAULT '' COMMENT '部署地址',
    doc_url VARCHAR(500) DEFAULT '' COMMENT '文档地址',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_teams_project (project_id)
) ENGINE=InnoDB COMMENT='小组表';

-- 小组成员表
CREATE TABLE IF NOT EXISTS team_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL COMMENT '所属小组',
    user_id INT NOT NULL COMMENT '成员',
    role_in_team VARCHAR(50) NOT NULL DEFAULT 'member' COMMENT '组内角色: leader/backend/frontend/database/crawler/devops',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    UNIQUE KEY uk_team_user (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_tm_team (team_id),
    INDEX idx_tm_user (user_id)
) ENGINE=InnoDB COMMENT='小组成员表';

-- ============================================================
-- 模块六：Bug 与问题管理（先建，模块四tasks引用它）
-- ============================================================

-- Bug表
CREATE TABLE IF NOT EXISTS bugs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(300) NOT NULL COMMENT 'Bug标题',
    description TEXT COMMENT 'Bug描述',
    repro_steps TEXT COMMENT '复现步骤',
    expected_result TEXT COMMENT '期望结果',
    actual_result TEXT COMMENT '实际结果',
    screenshot_url VARCHAR(500) DEFAULT '' COMMENT '截图',
    reporter_id INT NOT NULL COMMENT '提出人',
    assignee_id INT COMMENT '负责人',
    module VARCHAR(100) DEFAULT '' COMMENT '所属模块',
    severity ENUM('fatal','major','normal','minor','suggestion') DEFAULT 'normal' COMMENT '严重程度',
    status ENUM('new','confirmed','fixing','fixed','closed','wontfix') DEFAULT 'new' COMMENT '状态',
    solution TEXT COMMENT '解决方案',
    closed_at TIMESTAMP NULL COMMENT '关闭时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_bugs_reporter (reporter_id),
    INDEX idx_bugs_assignee (assignee_id),
    INDEX idx_bugs_status (status),
    INDEX idx_bugs_severity (severity),
    INDEX idx_bugs_module (module)
) ENGINE=InnoDB COMMENT='Bug表';

-- ============================================================
-- 模块四：任务看板
-- ============================================================

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '所属项目',
    team_id INT COMMENT '所属小组',
    title VARCHAR(300) NOT NULL COMMENT '任务标题',
    description TEXT COMMENT '任务描述',
    assignee_id INT COMMENT '负责人',
    priority ENUM('high','medium','low') DEFAULT 'medium' COMMENT '优先级',
    status ENUM('todo','in_progress','to_test','done','delayed','closed') DEFAULT 'todo' COMMENT '任务状态',
    start_date DATE COMMENT '开始日期',
    due_date DATE COMMENT '截止日期',
    estimated_hours DECIMAL(5,1) DEFAULT 0 COMMENT '预计工时(小时)',
    actual_hours DECIMAL(5,1) DEFAULT 0 COMMENT '实际工时(小时)',
    completion_note TEXT COMMENT '完成说明',
    screenshot_url VARCHAR(500) DEFAULT '' COMMENT '相关截图',
    related_bug_id INT COMMENT '关联Bug',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
    FOREIGN KEY (assignee_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (related_bug_id) REFERENCES bugs(id) ON DELETE SET NULL,
    INDEX idx_tasks_project (project_id),
    INDEX idx_tasks_team (team_id),
    INDEX idx_tasks_assignee (assignee_id),
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_priority (priority),
    INDEX idx_tasks_due (due_date)
) ENGINE=InnoDB COMMENT='任务表';

-- ============================================================
-- 模块五：每日实训日报
-- ============================================================

-- 日报表
CREATE TABLE IF NOT EXISTS daily_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '学生',
    team_id INT COMMENT '所属小组',
    report_date DATE NOT NULL COMMENT '所属日期',
    completed_content TEXT COMMENT '今日完成内容',
    problems_encountered TEXT COMMENT '遇到的问题',
    ai_tools_used VARCHAR(500) DEFAULT '' COMMENT '使用的AI工具',
    ai_help_summary TEXT COMMENT 'AI帮助解决了什么问题',
    code_commits TEXT COMMENT '今日代码提交记录',
    next_day_plan TEXT COMMENT '明日计划',
    self_score INT DEFAULT 3 COMMENT '自评完成度 1-5',
    teacher_comment TEXT COMMENT '教师点评',
    is_excellent TINYINT(1) DEFAULT 0 COMMENT '是否优秀日报',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_date (user_id, report_date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE SET NULL,
    INDEX idx_dr_user (user_id),
    INDEX idx_dr_team (team_id),
    INDEX idx_dr_date (report_date)
) ENGINE=InnoDB COMMENT='日报表';

-- ============================================================
-- 模块七：Python 爬虫数据采集模块
-- ============================================================

-- 爬虫采集任务配置表
CREATE TABLE IF NOT EXISTS crawler_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '采集任务名称',
    source_url VARCHAR(1000) NOT NULL COMMENT '采集数据源URL',
    source_type ENUM('job','tech_article','opensource','other') DEFAULT 'tech_article' COMMENT '数据源类型',
    keywords VARCHAR(500) DEFAULT '' COMMENT '采集关键词(逗号分隔)',
    cron_expr VARCHAR(100) DEFAULT '' COMMENT '定时表达式',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    request_interval INT DEFAULT 3 COMMENT '请求间隔(秒)',
    created_by INT COMMENT '创建人',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='爬虫采集任务配置表';

-- 爬虫采集数据表
CREATE TABLE IF NOT EXISTS crawler_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_id INT COMMENT '所属采集任务',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    url VARCHAR(1000) DEFAULT '' COMMENT '原文链接',
    summary TEXT COMMENT '摘要/描述',
    source_type ENUM('job','tech_article','opensource','other') DEFAULT 'tech_article' COMMENT '数据类型',
    keywords_matched VARCHAR(300) DEFAULT '' COMMENT '匹配关键词',
    raw_data JSON COMMENT '原始JSON数据',
    pub_date VARCHAR(50) DEFAULT '' COMMENT '发布时间',
    data_hash CHAR(64) DEFAULT '' COMMENT 'SHA256去重哈希',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (config_id) REFERENCES crawler_configs(id) ON DELETE SET NULL,
    UNIQUE KEY uk_data_hash (data_hash),
    INDEX idx_cd_type (source_type),
    INDEX idx_cd_config (config_id),
    INDEX idx_cd_keywords (keywords_matched)
) ENGINE=InnoDB COMMENT='爬虫采集数据表';

-- ============================================================
-- 模块八：AI 辅助开发记录模块
-- ============================================================

-- AI使用记录表
CREATE TABLE IF NOT EXISTS ai_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '使用人',
    task_id INT COMMENT '关联任务',
    tool_name VARCHAR(100) NOT NULL COMMENT 'AI工具名称',
    scene VARCHAR(100) NOT NULL COMMENT '使用场景',
    scene_category ENUM('db_design','flask_route','error_explain','style_optimize','test_case','dockerfile','compose','deploy_doc','log_analysis','project_summary','other') DEFAULT 'other' COMMENT '场景分类',
    prompt_text TEXT COMMENT '输入提示词',
    ai_output_summary TEXT COMMENT 'AI返回结果摘要',
    is_adopted TINYINT(1) DEFAULT 1 COMMENT '是否直接采用',
    has_modified TINYINT(1) DEFAULT 0 COMMENT '是否进行了修改',
    modification_note TEXT COMMENT '人工修改说明',
    effect_description TEXT COMMENT '最终解决效果',
    related_files VARCHAR(1000) DEFAULT '' COMMENT '相关代码文件',
    risk_note TEXT COMMENT '风险说明',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL,
    INDEX idx_ai_user (user_id),
    INDEX idx_ai_task (task_id),
    INDEX idx_ai_tool (tool_name),
    INDEX idx_ai_scene (scene_category),
    INDEX idx_ai_time (created_at)
) ENGINE=InnoDB COMMENT='AI使用记录表';

-- ============================================================
-- 模块九：数据统计与可视化（辅助表）
-- ============================================================

-- 评分表
CREATE TABLE IF NOT EXISTS scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL COMMENT '所属项目',
    team_id INT NOT NULL COMMENT '被评分小组',
    student_id INT COMMENT '被评分学生(个人评分)',
    scored_by INT NOT NULL COMMENT '评分人',
    category VARCHAR(100) NOT NULL COMMENT '评分维度',
    score DECIMAL(5,2) NOT NULL COMMENT '分数',
    max_score DECIMAL(5,2) DEFAULT 100 COMMENT '满分',
    comment TEXT COMMENT '评分备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (scored_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_scores_team (team_id),
    INDEX idx_scores_student (student_id),
    INDEX idx_scores_project (project_id)
) ENGINE=InnoDB COMMENT='评分表';

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT COMMENT '操作用户',
    action VARCHAR(100) NOT NULL COMMENT '操作类型',
    module VARCHAR(100) DEFAULT '' COMMENT '操作模块',
    target_type VARCHAR(50) DEFAULT '' COMMENT '操作对象类型',
    target_id INT DEFAULT 0 COMMENT '操作对象ID',
    detail JSON COMMENT '操作详情',
    ip_address VARCHAR(45) DEFAULT '' COMMENT '操作IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_sl_user (user_id),
    INDEX idx_sl_action (action),
    INDEX idx_sl_time (created_at)
) ENGINE=InnoDB COMMENT='系统日志表';

-- 公告表
CREATE TABLE IF NOT EXISTS announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(300) NOT NULL COMMENT '公告标题',
    content TEXT COMMENT '公告内容',
    publisher_id INT NOT NULL COMMENT '发布人',
    is_pinned TINYINT(1) DEFAULT 0 COMMENT '是否置顶',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (publisher_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_ann_time (created_at),
    INDEX idx_ann_pinned (is_pinned)
) ENGINE=InnoDB COMMENT='公告表';

-- ============================================================
-- 初始数据
-- ============================================================
INSERT INTO roles (name, display_name, description) VALUES
('admin', '管理员', '系统管理员，拥有所有权限'),
('teacher', '教师', '负责创建实训项目、查看进度、评分'),
('student', '学生', '参与实训项目、完成任务、提交日报');

-- 管理员账号: admin / admin123
INSERT INTO users (username, password_hash, real_name, email, role_id) VALUES
('admin', '$2b$12$LJ3m4ys3LkBCVxJGqOjPkuYVOYpGOKbHgEMoJxYzRqcMdFNP2oKCe', '系统管理员', 'admin@cloudhub.com', 1);
