from datetime import date, datetime

from flask import Blueprint, g, jsonify, request
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import or_

from .. import matching, settings_store
from ..extensions import db
from ..models import AuditLog, Category, FoundItem, Location, LostReport, MatchingResult
from ..security import (auth_required, can, error, hash_answer, new_salt, optional_auth,
                        permission_required, rate_limit)
from ..utils import UploadError, audit, clean, get_payload, notify, paginate, save_uploads

bp = Blueprint("items", __name__, url_prefix="/api")
DUP_THRESHOLD = 0.8


# ---------- shared helpers ----------
def parse_item(p):
    """Validate the fields common to lost and found reports. Returns (values, errors)."""
    errs, v = {}, {}
    v["title"] = clean(p.get("title"), 150)
    if len(v["title"]) < 3:
        errs["title"] = "Title must be at least 3 characters."
    v["description"] = clean(p.get("description"), 3000)
    if len(v["description"]) < 10:
        errs["description"] = "Description must be at least 10 characters."
    try:
        v["category_id"] = int(p.get("category_id"))
        if not db.session.get(Category, v["category_id"]) or not db.session.get(Category, v["category_id"]).is_active:
            raise ValueError
    except (TypeError, ValueError):
        errs["category_id"] = "Choose a valid category."
    try:
        v["location_id"] = int(p.get("location_id"))
        if not db.session.get(Location, v["location_id"]):
            raise ValueError
    except (TypeError, ValueError):
        errs["location_id"] = "Choose a valid campus location."
    try:
        v["date"] = datetime.strptime(str(p.get("date")), "%Y-%m-%d").date()
        if v["date"] > date.today():
            errs["date"] = "Date cannot be in the future."
    except ValueError:
        errs["date"] = "Enter a valid date (YYYY-MM-DD)."
    v["color"] = clean(p.get("color"), 40) or None
    v["brand"] = clean(p.get("brand"), 60) or None
    return v, errs


def find_duplicates(text, candidates):
    """Return candidates (obj, text) whose TF-IDF cosine similarity to `text` >= threshold."""
    if not candidates:
        return []
    try:
        m = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([text] + [t for _, t in candidates])
    except ValueError:
        return []
    sims = cosine_similarity(m[0], m[1:])[0]
    return [(o, float(s)) for (o, _), s in zip(candidates, sims) if s >= DUP_THRESHOLD]


def truthy(v):
    return str(v).lower() in ("1", "true", "yes", "on")


def like_filter(q, *cols):
    for tok in q.split()[:6]:
        esc = tok.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        yield or_(*[c.ilike(f"%{esc}%", escape="\\") for c in cols])


def moderation_hit(*texts):
    blob = " ".join(t or "" for t in texts).lower()
    return any(k.lower() in blob for k in settings_store.get("blocked_keywords") if k)


# ---------- LOST ----------
@bp.post("/lost")
@permission_required("lost.create")
@rate_limit("create_lost", 30, 3600)
def create_lost():
    p = get_payload()
    v, errs = parse_item(p)
    if errs:
        return error("Validation failed.", 422, fields=errs)
    text = f"{v['title']} {v['description']}"
    if not truthy(p.get("confirm_duplicate")):
        mine = LostReport.query.filter(LostReport.user_id == g.user.id, LostReport.category_id == v["category_id"],
                                       LostReport.status.in_(["open", "pending", "matched"])).all()
        dups = find_duplicates(text, [(r, f"{r.title} {r.description}") for r in mine])
        if dups:
            return error("A very similar report already exists.", 409, duplicate=True,
                         duplicates=[{"id": r.id, "title": r.title, "similarity": round(s * 100)} for r, s in dups])
    status = "pending" if moderation_hit(v["title"], v["description"], p.get("distinguishing_features")) else "open"
    report = LostReport(user_id=g.user.id, title=v["title"], category_id=v["category_id"], description=v["description"],
                        color=v["color"], brand=v["brand"], distinguishing_features=clean(p.get("distinguishing_features"), 2000) or None,
                        location_id=v["location_id"], lost_date=v["date"], status=status)
    db.session.add(report)
    db.session.flush()
    try:
        save_uploads(request.files.getlist("images"), lost_report_id=report.id)
    except UploadError as e:
        db.session.rollback()
        return error(str(e), 422, fields={"images": str(e)})
    audit("lost.create", g.user, "lost_report", report.id, moderated=status == "pending")
    db.session.flush()
    db.session.refresh(report)
    if status == "open":
        matching.run_for_lost(report)
    db.session.commit()
    return jsonify({"report": report.to_dict(), "matches": [matching.match_dict(r) for r in matching.ranked_for_lost(report.id, 5)]}), 201


@bp.get("/lost")
@auth_required
def list_lost():
    q = LostReport.query
    staff = can("items.review") and request.args.get("scope") == "all"
    if not staff:
        q = q.filter(LostReport.user_id == g.user.id)
    if (s := request.args.get("status")):
        q = q.filter(LostReport.status == s)
    if (t := clean(request.args.get("q"), 100)):
        for cond in like_filter(t, LostReport.title, LostReport.description):
            q = q.filter(cond)
    if (c := request.args.get("category_id", type=int)):
        q = q.filter(LostReport.category_id == c)
    q = q.order_by(LostReport.created_at.desc())
    return jsonify(paginate(q, lambda r: r.to_dict(owner=staff)))


def _own_or_staff_lost(rid):
    r = db.session.get(LostReport, rid)
    if not r or (r.user_id != g.user.id and not can("items.review")):
        return None   # 404 for others: do not reveal existence
    return r


@bp.get("/lost/<int:rid>")
@auth_required
def get_lost(rid):
    r = _own_or_staff_lost(rid)
    return jsonify({"report": r.to_dict()}) if r else error("Report not found.", 404)


@bp.put("/lost/<int:rid>")
@auth_required
def update_lost(rid):
    r = _own_or_staff_lost(rid)
    if not r or r.user_id != g.user.id:
        return error("Report not found.", 404)
    if r.status not in ("open", "pending"):
        return error("Only open reports can be edited.", 409)
    p = request.get_json(silent=True) or {}
    merged = {"title": r.title, "description": r.description, "category_id": r.category_id,
              "location_id": r.location_id, "date": r.lost_date.isoformat(), "color": r.color, "brand": r.brand}
    merged.update({k: p[k] for k in merged if k in p})
    v, errs = parse_item(merged)
    if errs:
        return error("Validation failed.", 422, fields=errs)
    r.title, r.description, r.category_id, r.location_id = v["title"], v["description"], v["category_id"], v["location_id"]
    r.lost_date, r.color, r.brand = v["date"], v["color"], v["brand"]
    if "distinguishing_features" in p:
        r.distinguishing_features = clean(p["distinguishing_features"], 2000) or None
    audit("lost.update", g.user, "lost_report", r.id)
    db.session.flush()
    if r.status == "open":
        matching.run_for_lost(r)
    db.session.commit()
    return jsonify({"report": r.to_dict()})


@bp.post("/lost/<int:rid>/close")
@auth_required
def close_lost(rid):
    r = _own_or_staff_lost(rid)
    if not r or r.user_id != g.user.id:
        return error("Report not found.", 404)
    if r.status in ("recovered", "closed"):
        return error("Report is already finished.", 409)
    r.status = "closed"
    MatchingResult.query.filter_by(lost_report_id=r.id).delete()
    audit("lost.close", g.user, "lost_report", r.id)
    db.session.commit()
    return jsonify({"report": r.to_dict()})


@bp.get("/lost/<int:rid>/matches")
@auth_required
def lost_matches(rid):
    r = _own_or_staff_lost(rid)
    if not r:
        return error("Report not found.", 404)
    if request.args.get("refresh") and r.status == "open":
        matching.run_for_lost(r)
        db.session.commit()
    return jsonify({"report": r.to_dict(), "matches": [matching.match_dict(m) for m in matching.ranked_for_lost(r.id)],
                    "min_score": settings_store.get("match_min_score"),
                    "disclaimer": "Suggestions only. Ownership must still be verified through a claim."})


@bp.get("/matches")
@auth_required
def my_matches():
    """All suggested matches across the current user's open lost reports."""
    reports = LostReport.query.filter(LostReport.user_id == g.user.id, LostReport.status == "open").all()
    out = []
    for r in reports:
        for m in matching.ranked_for_lost(r.id, 5):
            d = matching.match_dict(m)
            d["lost_report"] = {"id": r.id, "title": r.title}
            out.append(d)
    out.sort(key=lambda d: -d["score"])
    return jsonify({"matches": out})


@bp.post("/lost/<int:rid>/review")
@permission_required("items.review")
def review_lost(rid):
    r = db.session.get(LostReport, rid)
    if not r:
        return error("Report not found.", 404)
    p = request.get_json(silent=True) or {}
    decision, reason = p.get("decision"), clean(p.get("reason"), 255)
    if decision == "approve" and r.status == "pending":
        r.status = "open"
    elif decision == "reject" and r.status in ("pending", "open"):
        if len(reason) < 3:
            return error("A reason is required.", 422)
        r.status, r.status_reason = "rejected", reason
        MatchingResult.query.filter_by(lost_report_id=r.id).delete()
    elif decision == "archive":
        r.status = "archived"
        MatchingResult.query.filter_by(lost_report_id=r.id).delete()
    else:
        return error("Invalid decision for the report's current status.", 409)
    audit(f"lost.{decision}", g.user, "lost_report", r.id, reason=reason or None)
    notify(r.user_id, "report", f"Lost report {r.status}", f"Your report '{r.title}' is now {r.status}." + (f" Reason: {reason}" if reason else ""), f"/app/lost/{r.id}")
    db.session.flush()
    if r.status == "open":
        matching.run_for_lost(r)
    db.session.commit()
    return jsonify({"report": r.to_dict()})


# ---------- FOUND ----------
@bp.post("/found")
@permission_required("found.create")
@rate_limit("create_found", 30, 3600)
def create_found():
    p = get_payload()
    v, errs = parse_item(p)
    question, answer = clean(p.get("verification_question"), 255), clean(p.get("verification_answer"), 255)
    if bool(question) != bool(answer):
        errs["verification_answer"] = "Provide both a verification question and its answer (or neither)."
    if errs:
        return error("Validation failed.", 422, fields=errs)
    if not truthy(p.get("confirm_duplicate")):
        pool = FoundItem.query.filter(FoundItem.category_id == v["category_id"], FoundItem.location_id == v["location_id"],
                                      FoundItem.status.in_(["pending", "available"])).all()
        dups = find_duplicates(f"{v['title']} {v['description']}", [(f, f"{f.title} {f.public_description}") for f in pool])
        if dups:
            return error("A very similar found item is already registered.", 409, duplicate=True,
                         duplicates=[{"id": f.id, "title": f.title, "similarity": round(s * 100)} for f, s in dups])
    staff = can("items.review")
    status = "available" if staff and not moderation_hit(v["title"], v["description"]) else "pending"
    item = FoundItem(reporter_id=g.user.id, title=v["title"], category_id=v["category_id"], public_description=v["description"],
                     color=v["color"], brand=v["brand"], location_id=v["location_id"], found_date=v["date"],
                     private_details=clean(p.get("private_details"), 2000) or None,
                     storage_location=clean(p.get("storage_location"), 150) or None, status=status)
    if question:
        item.verification_question, item.verification_salt = question, new_salt()
        item.verification_answer_hash = hash_answer(answer, item.verification_salt)
    db.session.add(item)
    db.session.flush()
    try:
        save_uploads(request.files.getlist("images"), found_item_id=item.id)
    except UploadError as e:
        db.session.rollback()
        return error(str(e), 422, fields={"images": str(e)})
    audit("found.create", g.user, "found_item", item.id, status=status)
    db.session.flush()
    db.session.refresh(item)
    if status == "available":
        matching.run_for_found(item)
    else:
        for uid in _staff_ids("items.review"):
            notify(uid, "review", "Found item awaiting review", f"'{item.title}' needs approval.", "/app/admin/manage")
    db.session.commit()
    return jsonify({"item": item.to_private()}), 201


def _staff_ids(code):
    from ..models import Role, User
    return [u.id for u in User.query.join(Role).filter(User.is_active.is_(True)).all() if code in {p.code for p in u.role.permissions}]


def _can_see_private(item):
    return g.user is not None and (item.reporter_id == g.user.id or can("items.review") or can("claims.review"))


@bp.get("/found")
@optional_auth
def list_found():
    a = request.args
    q = FoundItem.query
    staff = can("items.review")
    if truthy(a.get("mine")):
        if g.user is None:
            return error("Authentication required.", 401)
        q = q.filter(FoundItem.reporter_id == g.user.id)
    elif staff and a.get("scope") == "all":
        pass
    else:
        q = q.filter(FoundItem.status == "available")
    if (s := a.get("status")) and (staff or truthy(a.get("mine"))):
        q = q.filter(FoundItem.status == s)
    if (t := clean(a.get("q"), 100)):
        for cond in like_filter(t, FoundItem.title, FoundItem.public_description, FoundItem.brand, FoundItem.color):
            q = q.filter(cond)
    if (c := a.get("category_id", type=int)):
        q = q.filter(FoundItem.category_id == c)
    if (l := a.get("location_id", type=int)):
        q = q.filter(FoundItem.location_id == l)
    if (col := clean(a.get("color"), 40)):
        q = q.filter(FoundItem.color.ilike(f"%{col.replace('%', '')}%"))
    for key, op in (("date_from", lambda d: FoundItem.found_date >= d), ("date_to", lambda d: FoundItem.found_date <= d)):
        if a.get(key):
            try:
                q = q.filter(op(datetime.strptime(a[key], "%Y-%m-%d").date()))
            except ValueError:
                return error(f"Invalid {key}.", 422)
    sort = a.get("sort", "newest")
    q = q.order_by({"oldest": FoundItem.found_date.asc(), "title": FoundItem.title.asc(),
                    "newest": FoundItem.found_date.desc()}.get(sort, FoundItem.found_date.desc()), FoundItem.id.desc())
    ser = (lambda f: f.to_private()) if (truthy(a.get("mine")) or (staff and a.get("scope") == "all")) else (lambda f: f.to_public())
    return jsonify(paginate(q, ser))


def _visible_found(fid):
    item = db.session.get(FoundItem, fid)
    if not item:
        return None
    if item.status == "available":
        return item
    if g.user is None:
        return None
    from ..models import Claim
    is_claimant = Claim.query.filter_by(found_item_id=fid, claimant_id=g.user.id).first() is not None
    return item if (_can_see_private(item) or is_claimant) else None


@bp.get("/found/<int:fid>")
@optional_auth
def get_found(fid):
    item = _visible_found(fid)
    if not item:
        return error("Item not found.", 404)
    if _can_see_private(item):
        d = item.to_private()
    else:
        d = item.to_public()
        if g.user is not None:
            d["verification_question"] = item.verification_question  # challenge only, never the answer
    return jsonify({"item": d})


@bp.put("/found/<int:fid>")
@auth_required
def update_found(fid):
    item = db.session.get(FoundItem, fid)
    if not item or (item.reporter_id != g.user.id and not can("items.review")):
        return error("Item not found.", 404)
    if item.status not in ("pending", "available"):
        return error("This item can no longer be edited.", 409)
    p = request.get_json(silent=True) or {}
    merged = {"title": item.title, "description": item.public_description, "category_id": item.category_id,
              "location_id": item.location_id, "date": item.found_date.isoformat(), "color": item.color, "brand": item.brand}
    merged.update({k: p[k] for k in merged if k in p})
    v, errs = parse_item(merged)
    if errs:
        return error("Validation failed.", 422, fields=errs)
    item.title, item.public_description, item.category_id, item.location_id = v["title"], v["description"], v["category_id"], v["location_id"]
    item.found_date, item.color, item.brand = v["date"], v["color"], v["brand"]
    for k in ("private_details", "storage_location"):
        if k in p:
            setattr(item, k, clean(p[k], 2000) or None)
    audit("found.update", g.user, "found_item", item.id)
    db.session.commit()
    return jsonify({"item": item.to_private()})


@bp.post("/found/<int:fid>/review")
@permission_required("items.review")
def review_found(fid):
    item = db.session.get(FoundItem, fid)
    if not item:
        return error("Item not found.", 404)
    p = request.get_json(silent=True) or {}
    decision, reason = p.get("decision"), clean(p.get("reason"), 255)
    if decision == "approve" and item.status == "pending":
        item.status = "available"
    elif decision == "reject" and item.status in ("pending", "available"):
        if len(reason) < 3:
            return error("A reason is required.", 422)
        item.status, item.status_reason = "rejected", reason
        MatchingResult.query.filter_by(found_item_id=item.id).delete()
    elif decision == "archive" and item.status in ("available", "returned", "rejected"):
        item.status = "archived"
        MatchingResult.query.filter_by(found_item_id=item.id).delete()
    else:
        return error("Invalid decision for the item's current status.", 409)
    audit(f"found.{decision}", g.user, "found_item", item.id, reason=reason or None)
    notify(item.reporter_id, "report", f"Found item {item.status}", f"'{item.title}' is now {item.status}." + (f" Reason: {reason}" if reason else ""), f"/app/my-reports")
    db.session.flush()
    if item.status == "available":
        matching.run_for_found(item)
    db.session.commit()
    return jsonify({"item": item.to_private()})


LABELS = {"found.create": "Item registered", "found.approve": "Approved and published", "found.reject": "Rejected",
          "found.archive": "Archived", "found.update": "Details updated", "claim.submit": "Ownership claim submitted",
          "claim.approve": "Claim approved - ready for collection", "claim.reject": "Claim rejected",
          "handover.complete": "Handed over to the verified owner"}


@bp.get("/found/<int:fid>/timeline")
@optional_auth
def timeline(fid):
    """Public-safe lifecycle: action labels and timestamps only (no user identities)."""
    item = _visible_found(fid)
    if not item:
        return error("Item not found.", 404)
    rows = (AuditLog.query.filter(AuditLog.entity_type.in_(["found_item", "claim", "handover"]),
                                  AuditLog.action.in_(list(LABELS))).order_by(AuditLog.created_at).all())
    events = [{"label": LABELS[r.action], "at": r.created_at.isoformat()} for r in rows
              if (r.entity_type == "found_item" and r.entity_id == fid) or (r.details or {}).get("found_item_id") == fid]
    return jsonify({"status": item.status, "events": events})
