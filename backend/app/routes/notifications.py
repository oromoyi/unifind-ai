from flask import Blueprint, g, jsonify, request

from ..extensions import db
from ..models import Notification
from ..security import auth_required, error
from ..utils import paginate

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
@auth_required
def list_notifications():
    q = Notification.query.filter_by(user_id=g.user.id)
    if request.args.get("unread") == "1":
        q = q.filter_by(is_read=False)
    data = paginate(q.order_by(Notification.created_at.desc(), Notification.id.desc()), lambda n: n.to_dict(), 20)
    data["unread"] = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
    return jsonify(data)


@bp.get("/unread-count")
@auth_required
def unread_count():
    return jsonify({"unread": Notification.query.filter_by(user_id=g.user.id, is_read=False).count()})


@bp.post("/<int:nid>/read")
@auth_required
def mark_read(nid):
    n = db.session.get(Notification, nid)
    if not n or n.user_id != g.user.id:
        return error("Notification not found.", 404)
    n.is_read = True
    db.session.commit()
    return jsonify({"notification": n.to_dict()})


@bp.post("/read-all")
@auth_required
def read_all():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read."})
