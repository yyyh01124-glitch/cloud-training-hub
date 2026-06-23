from flask import Blueprint, render_template, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Notification

notif_bp = Blueprint('notification', __name__)


@notif_bp.route('/')
@login_required
def list_notifications():
    page = int(__import__('flask').request.args.get('page', 1))
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20)
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('notifications/list.html', notifs=notifs, unread=unread)


@notif_bp.route('/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})


@notif_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return redirect(url_for('notification.list_notifications'))


@notif_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    n = db.session.get(Notification, notif_id)
    if n and n.user_id == current_user.id:
        n.is_read = True
        db.session.commit()
    if n and n.link:
        return redirect(n.link)
    return redirect(url_for('notification.list_notifications'))
