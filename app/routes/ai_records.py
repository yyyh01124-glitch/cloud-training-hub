from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import AiRecord, Task

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/')
@login_required
def list_records():
    page = request.args.get('page', 1, type=int)
    tool = request.args.get('tool', '')
    scene = request.args.get('scene', '')

    query = AiRecord.query
    if current_user.role.name == 'student':
        query = query.filter_by(user_id=current_user.id)
    if tool:
        query = query.filter_by(tool_name=tool)
    if scene:
        query = query.filter_by(scene_category=scene)

    records = query.order_by(AiRecord.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('ai_records/list.html', records=records, tool_filter=tool, scene_filter=scene)


@ai_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_record():
    if request.method == 'POST':
        record = AiRecord(
            user_id=current_user.id,
            task_id=request.form.get('task_id', type=int) or None,
            tool_name=request.form.get('tool_name', '').strip(),
            scene=request.form.get('scene', ''),
            scene_category=request.form.get('scene_category', 'other'),
            prompt_text=request.form.get('prompt_text', ''),
            ai_output_summary=request.form.get('ai_output_summary', ''),
            is_adopted=request.form.get('is_adopted') == 'on',
            has_modified=request.form.get('has_modified') == 'on',
            modification_note=request.form.get('modification_note', ''),
            effect_description=request.form.get('effect_description', ''),
            related_files=request.form.get('related_files', ''),
            risk_note=request.form.get('risk_note', '')
        )
        db.session.add(record)
        db.session.commit()
        flash('AI 使用记录已保存', 'success')
        return redirect(url_for('ai.list_records'))
    tasks = Task.query.filter_by(assignee_id=current_user.id).all()
    return render_template('ai_records/form.html', tasks=tasks)


@ai_bp.route('/<int:record_id>')
@login_required
def record_detail(record_id):
    record = db.session.get(AiRecord, record_id)
    if not record:
        flash('记录不存在', 'danger')
        return redirect(url_for('ai.list_records'))
    return render_template('ai_records/detail.html', record=record)


@ai_bp.route('/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_record(record_id):
    record = db.session.get(AiRecord, record_id)
    if not record:
        flash('记录不存在', 'danger')
        return redirect(url_for('ai.list_records'))
    if record.user_id != current_user.id and current_user.role.name == 'student':
        flash('只能编辑自己的记录', 'danger')
        return redirect(url_for('ai.list_records'))
    if request.method == 'POST':
        record.tool_name = request.form.get('tool_name', '').strip()
        record.scene = request.form.get('scene', '')
        record.scene_category = request.form.get('scene_category', 'other')
        record.prompt_text = request.form.get('prompt_text', '')
        record.ai_output_summary = request.form.get('ai_output_summary', '')
        record.is_adopted = request.form.get('is_adopted') == 'on'
        record.has_modified = request.form.get('has_modified') == 'on'
        record.modification_note = request.form.get('modification_note', '')
        record.effect_description = request.form.get('effect_description', '')
        record.related_files = request.form.get('related_files', '')
        record.risk_note = request.form.get('risk_note', '')
        db.session.commit()
        flash('记录已更新', 'success')
        return redirect(url_for('ai.record_detail', record_id=record.id))
    tasks = Task.query.all()
    return render_template('ai_records/form.html', record=record, tasks=tasks)


@ai_bp.route('/cases')
@login_required
def case_library():
    scene = request.args.get('scene', '')
    tool = request.args.get('tool', '')
    query = AiRecord.query.filter(AiRecord.is_adopted == True).filter(AiRecord.prompt_text != '')
    if scene:
        query = query.filter_by(scene_category=scene)
    if tool:
        query = query.filter_by(tool_name=tool)
    records = query.order_by(AiRecord.created_at.desc()).limit(30).all()
    return render_template('ai_records/cases.html', records=records, scene_filter=scene, tool_filter=tool)


@ai_bp.route('/stats')
@login_required
def ai_stats():
    from sqlalchemy import func as safunc
    by_tool = db.session.query(AiRecord.tool_name, safunc.count(AiRecord.id)).group_by(AiRecord.tool_name).all()
    by_scene = db.session.query(AiRecord.scene_category, safunc.count(AiRecord.id)).group_by(AiRecord.scene_category).all()
    by_user = db.session.query(User.real_name, safunc.count(AiRecord.id)).join(AiRecord).group_by(User.id).all()
    adopted = AiRecord.query.filter_by(is_adopted=True).count()
    modified = AiRecord.query.filter_by(has_modified=True).count()
    total = AiRecord.query.count()
    return render_template('ai_records/stats.html',
                           by_tool=[{'name': t, 'value': c} for t, c in by_tool],
                           by_scene=[{'name': t, 'value': c} for t, c in by_scene],
                           by_user=[{'name': t, 'value': c} for t, c in by_user],
                           adopted=adopted, modified=modified, total=total)


@ai_bp.route('/<int:record_id>/delete', methods=['POST'])
@login_required
def delete_record(record_id):
    record = db.session.get(AiRecord, record_id)
    if record and (current_user.role.name in ('admin', 'teacher') or record.user_id == current_user.id):
        db.session.delete(record)
        db.session.commit()
        flash('记录已删除', 'success')
    return redirect(url_for('ai.list_records'))
