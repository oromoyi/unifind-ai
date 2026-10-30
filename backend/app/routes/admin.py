import csv
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, Response, g, jsonify, request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from .. import evaluation, matching, settings_store
from ..extensions import db
from ..models import (utcnow, AuditLog, Category, Claim, ContactMessage, Feedback, FoundItem, Handover, Location,
                      LostReport, MatchingResult, Permission, Role, User)
from ..security import (error, hash_password, password_problem, permission_required)
from ..utils import audit, clean, paginate

bp = Blueprint("admin", __name__, url_prefix="/api/admin")
STAFF_ROLES = {"student", "finder", "officer", "admin"}


# ---------- users & roles ----------
@bp.get("/users")
@permission_required("users.manage")
def users():
    q = User.query
    if (r := request.args.get("role")):
        q = q.join(Role).filter(Role.name == r)
    if (t := clean(request.args.get("q"), 80)):
        like = f"%{t.replace('%', '')}%"
        q = q.filter((User.full_name.ilike(like)) | (User.email.ilike(like)) | (User.student_id.ilike(like)))
    return jsonify(paginate(q.order_by(User.created_at.desc()), lambda u: u.to_admin(), 15))


@bp.post("/users")
@permission_required("users.manage")
def create_user():
    p = request.get_json(silent=True) or {}
    role = Role.query.filter_by(name=clean(p.get("role"))).first()
    email = clean(p.get("email"), 190).lower()
    errs = {}
    if not role:
        errs["role"] = "Invalid role."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errs["email"] = "Invalid email."
    elif User.query.filter(func.lower(User.email) == email).first():
        errs["email"] = "Email already registered."
    if len(clean(p.get("full_name"))) < 2:
        errs["full_name"] = "Name is required."
    if (m := password_problem(p.get("password"))):
        errs["password"] = m
    if errs:
        return error("Validation failed.", 422, fields=errs)
    u = User(full_name=clean(p["full_name"], 120), email=email, password_hash=hash_password(p["password"]), role_id=role.id,
             department=clean(p.get("department"), 120) or None)
    db.session.add(u)
    db.session.flush()
    audit("admin.user_create", g.user, "user", u.id, role=role.name)
    db.session.commit()
    return jsonify({"user": u.to_admin()}), 201


@bp.put("/users/<int:uid>")
@permission_required("users.manage")
def update_user(uid):
    u = db.session.get(User, uid)
    if not u:
        return error("User not found.", 404)
    p = request.get_json(silent=True) or {}
    changes = {}
    if "role" in p:
        role = Role.query.filter_by(name=p["role"]).first()
        if not role:
            return error("Invalid role.", 422)
        if u.id == g.user.id and role.name != "admin":
            return error("You cannot remove your own administrator role.", 409)
        if u.role_id != role.id:
            changes["role"] = [u.role.name, role.name]
            u.role_id = role.id
            db.session.flush(); db.session.refresh(u)
    if "is_active" in p:
        if u.id == g.user.id and not p["is_active"]:
            return error("You cannot deactivate your own account.", 409)
        if u.is_active != bool(p["is_active"]):
            changes["is_active"] = bool(p["is_active"])
            u.is_active = bool(p["is_active"])
    if p.get("unlock"):
        u.locked_until, u.failed_logins = None, 0
        changes["unlock"] = True
    audit("admin.user_update", g.user, "user", u.id, **changes)
    db.session.commit()
    return jsonify({"user": u.to_admin()})


@bp.get("/roles")
@permission_required("roles.manage")
def roles():
    return jsonify({"roles": [{"id": r.id, "name": r.name, "description": r.description,
                               "permissions": sorted(p.code for p in r.permissions)} for r in Role.query.order_by(Role.id)],
                    "permissions": [{"code": p.code, "description": p.description} for p in Permission.query.order_by(Permission.code)]})


@bp.put("/roles/<int:rid>/permissions")
@permission_required("roles.manage")
def set_permissions(rid):
    role = db.session.get(Role, rid)
    if not role:
        return error("Role not found.", 404)
    if role.name == "admin":
        return error("The administrator role always has every permission.", 409)
    codes = (request.get_json(silent=True) or {}).get("permissions")
    if not isinstance(codes, list):
        return error("permissions must be a list.", 422)
    perms = Permission.query.filter(Permission.code.in_(codes)).all()
    role.permissions = perms
    audit("admin.role_permissions", g.user, "role", role.id, permissions=sorted(p.code for p in perms))
    db.session.commit()
    return jsonify({"role": {"id": role.id, "name": role.name, "permissions": sorted(p.code for p in role.permissions)}})


# ---------- catalogue ----------
def _catalog(model, label):
    @bp.post(f"/{label}", endpoint=f"create_{label}")
    @permission_required("settings.manage")
    def create():
        p = request.get_json(silent=True) or {}
        name = clean(p.get("name"), 120)
        if len(name) < 2:
            return error("Name is required.", 422, fields={"name": "Required"})
        if model.query.filter(func.lower(model.name) == name.lower()).first():
            return error("That name already exists.", 409, fields={"name": "Already exists"})
        extra = {k: p.get(k) for k in ("zone", "x", "y") if model is Location and k in p}
        obj = model(name=name, **extra)
        db.session.add(obj)
        db.session.flush()
        audit(f"admin.{label}_create", g.user, label, obj.id, name=name)
        db.session.commit()
        return jsonify({label: obj.to_dict()}), 201

    @bp.put(f"/{label}/<int:oid>", endpoint=f"update_{label}")
    @permission_required("settings.manage")
    def update(oid):
        obj = db.session.get(model, oid)
        if not obj:
            return error("Not found.", 404)
        p = request.get_json(silent=True) or {}
        if "name" in p and len(clean(p["name"])) >= 2:
            obj.name = clean(p["name"], 120)
        if "is_active" in p:
            obj.is_active = bool(p["is_active"])
        if model is Location:
            for k in ("zone", "x", "y"):
                if k in p:
                    setattr(obj, k, p[k])
        audit(f"admin.{label}_update", g.user, label, obj.id)
        db.session.commit()
        return jsonify({label: obj.to_dict()})

    @bp.get(f"/{label}", endpoint=f"list_{label}")
    @permission_required("settings.manage")
    def lst():
        return jsonify({"items": [o.to_dict() for o in model.query.order_by(model.name)]})


_catalog(Category, "categories")
_catalog(Location, "locations")


# ---------- settings ----------
@bp.get("/settings")
@permission_required("settings.manage")
def get_settings():
    return jsonify({"settings": settings_store.all_settings()})


@bp.put("/settings")
@permission_required("settings.manage")
def put_settings():
    p = request.get_json(silent=True) or {}
    errs = {}
    if "match_weights" in p:
        w = p["match_weights"]
        keys = set(settings_store.DEFAULTS["match_weights"])
        try:
            if set(w) != keys or any(float(v) < 0 for v in w.values()) or sum(float(v) for v in w.values()) <= 0:
                raise ValueError
            p["match_weights"] = {k: float(v) for k, v in w.items()}
        except (ValueError, TypeError):
            errs["match_weights"] = f"Provide non-negative numbers for: {', '.join(sorted(keys))}."
    for k in ("match_min_score", "match_notify_score"):
        if k in p:
            try:
                p[k] = float(p[k]); assert 0 <= p[k] <= 100
            except (ValueError, TypeError, AssertionError):
                errs[k] = "Must be between 0 and 100."
    for k, lo, hi in (("match_max_results", 1, 50), ("max_claim_attempts", 1, 10)):
        if k in p:
            try:
                p[k] = int(p[k]); assert lo <= p[k] <= hi
            except (ValueError, TypeError, AssertionError):
                errs[k] = f"Must be between {lo} and {hi}."
    if "student_id_pattern" in p:
        try:
            re.compile(p["student_id_pattern"])
        except (re.error, TypeError):
            errs["student_id_pattern"] = "Invalid regular expression."
    for k in ("blocked_keywords", "departments"):
        if k in p and not (isinstance(p[k], list) and all(isinstance(i, str) for i in p[k])):
            errs[k] = "Must be a list of strings."
    if errs:
        return error("Validation failed.", 422, fields=errs)
    for k in settings_store.DEFAULTS:
        if k in p:
            settings_store.put(k, p[k])
    audit("admin.settings_update", g.user, "settings", None, keys=[k for k in p if k in settings_store.DEFAULTS])
    db.session.commit()
    return jsonify({"settings": settings_store.all_settings()})


@bp.post("/rematch")
@permission_required("settings.manage")
def rematch():
    n = 0
    for r in LostReport.query.filter_by(status="open").all():
        matching.run_for_lost(r)
        n += 1
    audit("admin.rematch", g.user, "settings", None, reports=n)
    db.session.commit()
    return jsonify({"message": f"Recomputed matches for {n} open lost reports."})


@bp.get("/audit")
@permission_required("audit.view")
def audit_logs():
    q = AuditLog.query
    if (a := clean(request.args.get("action"), 60)):
        q = q.filter(AuditLog.action.like(f"{a.replace('%', '')}%"))
    if (e := clean(request.args.get("entity_type"), 40)):
        q = q.filter(AuditLog.entity_type == e)
    return jsonify(paginate(q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()), lambda a: a.to_dict(), 25))


@bp.get("/contact-messages")
@permission_required("users.manage")
def contact_messages():
    rows = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(100).all()
    return jsonify({"items": [{"id": m.id, "name": m.name, "email": m.email, "message": m.message,
                               "created_at": m.created_at.isoformat()} for m in rows]})


# ---------- analytics ----------
def compute_analytics():
    found = FoundItem.query.all()
    lost = LostReport.query.all()
    handovers = Handover.query.filter_by(status="completed").all()
    published = [f for f in found if f.status in ("available", "claimed", "returned", "archived")]
    returned = [f for f in found if f.status == "returned"]
    hours = [(h.completed_at - h.item.created_at).total_seconds() / 3600 for h in handovers if h.completed_at]
    since = utcnow().replace(day=1)
    months = []
    for i in range(5, -1, -1):
        y, m = since.year, since.month - i
        while m <= 0:
            y, m = y - 1, m + 12
        months.append((y, m))
    series = {k: Counter() for k in ("lost", "found", "returned")}
    for r in lost:
        series["lost"][(r.created_at.year, r.created_at.month)] += 1
    for f in found:
        series["found"][(f.created_at.year, f.created_at.month)] += 1
    for h in handovers:
        series["returned"][(h.completed_at.year, h.completed_at.month)] += 1
    by_cat = defaultdict(lambda: {"lost": 0, "found": 0})
    for r in lost:
        by_cat[r.category.name]["lost"] += 1
    for f in found:
        by_cat[f.category.name]["found"] += 1
    ratings = [x.rating for x in Feedback.query.all()]
    # operational matcher quality: for completed returns linked to a lost report, was the item suggested?
    linked = [(h, db.session.get(Claim, h.claim_id)) for h in handovers]
    linked = [(h, c) for h, c in linked if c.lost_report_id]
    return {
        "kpis": {
            "total_users": User.query.count(), "lost_reports": len(lost), "found_items": len(found),
            "available_items": sum(f.status == "available" for f in found),
            "pending_review": sum(f.status == "pending" for f in found) + sum(r.status == "pending" for r in lost),
            "pending_claims": Claim.query.filter_by(status="pending").count(),
            "suspicious_claims": Claim.query.filter_by(status="pending", suspicious=True).count(),
            "returned_items": len(returned),
            "recovery_rate_pct": round(100 * len(returned) / len(published), 1) if published else 0.0,
            "avg_time_to_recovery_hours": round(sum(hours) / len(hours), 1) if hours else None,
            "avg_feedback_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "feedback_count": len(ratings),
        },
        "monthly": [{"month": f"{y}-{m:02d}", "lost": series["lost"][(y, m)], "found": series["found"][(y, m)],
                     "returned": series["returned"][(y, m)]} for y, m in months],
        "by_category": [{"category": k, **v} for k, v in sorted(by_cat.items())],
        "found_status": [{"status": s, "count": c} for s, c in sorted(Counter(f.status for f in found).items())],
        "claim_status": [{"status": s, "count": c} for s, c in sorted(Counter(c.status for c in Claim.query.all()).items())],
        "operational_matching": {"completed_returns_linked_to_report": len(linked),
                                 "returned_item_was_suggested": sum(1 for h, c in linked if MatchingResult.query.filter_by(lost_report_id=c.lost_report_id, found_item_id=h.found_item_id).first()),
                                 "note": "Matches are deleted when an item leaves 'available', so this count only covers pairs still stored."},
    }


@bp.get("/analytics")
@permission_required("analytics.view")
def analytics():
    return jsonify(compute_analytics())


@bp.get("/evaluation")
@permission_required("analytics.view")
def eval_endpoint():
    result = evaluation.run_evaluation(settings_store.get("match_weights"))
    result["methodology"] = [
        "Dataset: labelled lost/found pairs (synthetic by default). Each lost report has exactly one true found item.",
        "Baseline: keyword search - rank found items by number of shared keywords (no category, place or date).",
        "Matcher: weighted score of category, TF-IDF description similarity, colour/brand, location, date (current admin weights).",
        "Ranking metrics: Precision@1, Hit-rate@k (true item in top k), Mean Reciprocal Rank.",
        "Classification metrics: precision/recall/F1 over all lost-found pairs at several score thresholds.",
        "Limitations: synthetic text is cleaner than real reports; the baseline has no access to location/date metadata.",
    ]
    return jsonify(result)


# ---------- exports ----------
def _safe(v):
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s   # CSV/formula-injection guard


def export_rows(kind):
    if kind == "found-items":
        h = ["ID", "Title", "Category", "Location", "Found date", "Status", "Registered"]
        return h, [[f.id, f.title, f.category.name, f.location.name, f.found_date, f.status, f.created_at.date()]
                   for f in FoundItem.query.order_by(FoundItem.id)]
    if kind == "lost-reports":
        h = ["ID", "Title", "Category", "Location", "Lost date", "Status", "Reported"]
        return h, [[r.id, r.title, r.category.name, r.location.name, r.lost_date, r.status, r.created_at.date()]
                   for r in LostReport.query.order_by(LostReport.id)]
    if kind == "claims":
        h = ["ID", "Item", "Status", "Suspicious", "Flag reason", "Submitted", "Reviewed"]
        return h, [[c.id, c.item.title, c.status, "yes" if c.suspicious else "no", c.flag_reason, c.created_at.date(),
                    c.reviewed_at.date() if c.reviewed_at else ""] for c in Claim.query.order_by(Claim.id)]
    if kind == "summary":
        k = compute_analytics()["kpis"]
        return ["Metric", "Value"], [[a.replace("_", " ").capitalize(), b if b is not None else "n/a"] for a, b in k.items()]
    return None, None


@bp.get("/export/<kind>")
@permission_required("reports.export")
def export(kind):
    header, rows = export_rows(kind)
    if header is None:
        return error("Unknown report.", 404)
    fmt = request.args.get("format", "csv")
    audit("report.export", g.user, "report", None, kind=kind, format=fmt)
    db.session.commit()
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(header)
        w.writerows([[_safe(c) for c in r] for r in rows])
        return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={kind}.csv"})
    if fmt == "pdf":
        out = io.BytesIO()
        doc = SimpleDocTemplate(out, pagesize=landscape(A4), title=f"UniFind AI - {kind}")
        st = getSampleStyleSheet()
        data = [header] + [[str(c)[:40] if c is not None else "" for c in r] for r in rows]
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b2545")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef6f6")])]))
        doc.build([Paragraph(f"{settings_store.get('university_name')} - UniFind AI report: {kind.replace('-', ' ')}", st["Title"]),
                   Paragraph(f"Generated {utcnow():%Y-%m-%d %H:%M} UTC by {g.user.full_name}", st["Normal"]),
                   Spacer(1, 12), t])
        return Response(out.getvalue(), mimetype="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={kind}.pdf"})
    return error("format must be csv or pdf.", 422)
