from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Announcement
from app.utils.decorators import role_required, send_notification

announcement_bp = Blueprint('announcement', __name__)


@announcement_bp.route('/')
@login_required
def list_announcements():
    page = request.args.get('page', 1, type=int)
    announcements = Announcement.query.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('admin/announcements.html', announcements=announcements)


@announcement_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def create_announcement():
    if request.method == 'POST':
        a = Announcement(
            title=request.form.get('title', '').strip(),
            content=request.form.get('content', ''),
            publisher_id=current_user.id,
            is_pinned=request.form.get('is_pinned') == 'on'
        )
        db.session.add(a)
        db.session.commit()
        flash('公告已发布', 'success')
        return redirect(url_for('announcement.list_announcements'))
    return render_template('admin/announcement_form.html')


@announcement_bp.route('/<int:ann_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'teacher')
def edit_announcement(ann_id):
    a = db.session.get(Announcement, ann_id)
    if not a:
        flash('公告不存在', 'danger')
        return redirect(url_for('announcement.list_announcements'))
    if request.method == 'POST':
        a.title = request.form.get('title', '').strip()
        a.content = request.form.get('content', '')
        a.is_pinned = request.form.get('is_pinned') == 'on'
        db.session.commit()
        flash('公告已更新', 'success')
        return redirect(url_for('announcement.list_announcements'))
    return render_template('admin/announcement_form.html', announcement=a)


@announcement_bp.route('/<int:ann_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_announcement(ann_id):
    a = db.session.get(Announcement, ann_id)
    if a:
        db.session.delete(a)
        db.session.commit()
        flash('公告已删除', 'success')
    return redirect(url_for('announcement.list_announcements'))
