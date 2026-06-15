from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import CrawlerConfig, CrawlerData

crawler_bp = Blueprint('crawler', __name__)


@crawler_bp.route('/configs')
@login_required
def list_configs():
    configs = CrawlerConfig.query.order_by(CrawlerConfig.created_at.desc()).all()
    return render_template('crawler/configs.html', configs=configs)


@crawler_bp.route('/configs/create', methods=['GET', 'POST'])
@login_required
def create_config():
    if current_user.role.name not in ('admin', 'teacher'):
        flash('无权限', 'danger')
        return redirect(url_for('crawler.list_configs'))
    if request.method == 'POST':
        config = CrawlerConfig(
            name=request.form.get('name', '').strip(),
            source_url=request.form.get('source_url', '').strip(),
            source_type=request.form.get('source_type', 'tech_article'),
            keywords=request.form.get('keywords', ''),
            cron_expr=request.form.get('cron_expr', ''),
            request_interval=request.form.get('request_interval', type=int) or 3,
            created_by=current_user.id
        )
        db.session.add(config)
        db.session.commit()
        flash('爬虫配置已创建', 'success')
        return redirect(url_for('crawler.list_configs'))
    return render_template('crawler/config_form.html')


@crawler_bp.route('/configs/<int:config_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_config(config_id):
    config = db.session.get(CrawlerConfig, config_id)
    if not config:
        flash('配置不存在', 'danger')
        return redirect(url_for('crawler.list_configs'))
    if request.method == 'POST':
        config.name = request.form.get('name', '').strip()
        config.source_url = request.form.get('source_url', '').strip()
        config.source_type = request.form.get('source_type', 'tech_article')
        config.keywords = request.form.get('keywords', '')
        config.cron_expr = request.form.get('cron_expr', '')
        config.request_interval = request.form.get('request_interval', type=int) or 3
        db.session.commit()
        flash('配置已更新', 'success')
        return redirect(url_for('crawler.list_configs'))
    return render_template('crawler/config_form.html', config=config)


@crawler_bp.route('/configs/<int:config_id>/toggle', methods=['POST'])
@login_required
def toggle_config(config_id):
    config = db.session.get(CrawlerConfig, config_id)
    if config:
        config.is_active = not config.is_active
        db.session.commit()
    return redirect(url_for('crawler.list_configs'))


@crawler_bp.route('/configs/<int:config_id>/delete', methods=['POST'])
@login_required
def delete_config(config_id):
    config = db.session.get(CrawlerConfig, config_id)
    if config and current_user.role.name == 'admin':
        db.session.delete(config)
        db.session.commit()
        flash('配置已删除', 'success')
    return redirect(url_for('crawler.list_configs'))


@crawler_bp.route('/configs/<int:config_id>/run', methods=['POST'])
@login_required
def run_crawl(config_id):
    config = db.session.get(CrawlerConfig, config_id)
    if not config:
        flash('配置不存在', 'danger')
        return redirect(url_for('crawler.list_configs'))
    try:
        from crawler.spider import crawl_url
        results = crawl_url(config.source_url, config.source_type)
        from crawler.parser import parse_and_save
        count = parse_and_save(results, config)
        flash(f'采集完成，新增 {count} 条数据', 'success')
    except Exception as e:
        flash(f'采集失败: {str(e)}', 'danger')
    return redirect(url_for('crawler.data_list'))


@crawler_bp.route('/stats')
@login_required
def stats():
    from sqlalchemy import func as safunc
    type_data = db.session.query(
        CrawlerData.source_type, safunc.count(CrawlerData.id)
    ).group_by(CrawlerData.source_type).all()
    config_data = db.session.query(
        CrawlerConfig.name, safunc.count(CrawlerData.id)
    ).join(CrawlerData, CrawlerData.config_id == CrawlerConfig.id, isouter=True
    ).group_by(CrawlerConfig.id).all()
    return render_template('crawler/stats.html',
                           type_data=[{'name': t, 'value': c} for t, c in type_data],
                           config_data=[{'name': n or '无配置', 'value': c} for n, c in config_data],
                           total=CrawlerData.query.count())


@crawler_bp.route('/data')
@login_required
def data_list():
    page = request.args.get('page', 1, type=int)
    source_type = request.args.get('source_type', '')
    search = request.args.get('search', '').strip()

    query = CrawlerData.query
    if source_type:
        query = query.filter_by(source_type=source_type)
    if search:
        query = query.filter(CrawlerData.title.contains(search))

    data = query.order_by(CrawlerData.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('crawler/data_list.html', data=data, type_filter=source_type, search=search)


@crawler_bp.route('/data/<int:data_id>')
@login_required
def data_detail(data_id):
    entry = db.session.get(CrawlerData, data_id)
    if not entry:
        flash('数据不存在', 'danger')
        return redirect(url_for('crawler.data_list'))
    return render_template('crawler/data_detail.html', entry=entry)
