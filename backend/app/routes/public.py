from flask import Blueprint, jsonify, request
from sqlalchemy import func

from .. import settings_store
from ..extensions import db
from ..models import Category, ContactMessage, FoundItem, Location, LostReport
from ..security import error, rate_limit
from ..utils import clean

bp = Blueprint("public", __name__, url_prefix="/api")


@bp.get("/meta")
def meta():
    return jsonify({
        "categories": [c.to_dict() for c in Category.query.filter_by(is_active=True).order_by(Category.name)],
        "locations": [l.to_dict() for l in Location.query.filter_by(is_active=True).order_by(Location.name)],
        "university_name": settings_store.get("university_name"),
        "departments": settings_store.get("departments"),
    })


@bp.get("/stats/public")
def public_stats():
    count = lambda q: db.session.scalar(q) or 0
    available = count(db.select(func.count(FoundItem.id)).where(FoundItem.status == "available"))
    returned = count(db.select(func.count(FoundItem.id)).where(FoundItem.status == "returned"))
    handled = count(db.select(func.count(FoundItem.id)).where(FoundItem.status.in_(["available", "claimed", "returned", "archived"])))
    lost = count(db.select(func.count(LostReport.id)).where(LostReport.status.in_(["open", "matched", "recovered", "closed"])))
    return jsonify({"available_found": available, "returned": returned, "lost_reports": lost,
                    "recovery_rate": round(100 * returned / handled, 1) if handled else 0.0})


@bp.post("/contact")
@rate_limit("contact", 5, 3600)
def contact():
    p = request.get_json(silent=True) or {}
    name, email, msg = clean(p.get("name"), 120), clean(p.get("email"), 190), clean(p.get("message"), 3000)
    if len(name) < 2 or "@" not in email or len(msg) < 10:
        return error("Please provide your name, a valid email and a message (10+ characters).", 422)
    db.session.add(ContactMessage(name=name, email=email, message=msg))
    db.session.commit()
    return jsonify({"message": "Thank you. Your message has been received."}), 201
