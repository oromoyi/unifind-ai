import io
from datetime import timedelta

from flask import Blueprint, g, jsonify, request, send_file
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas

from .. import matching, security, settings_store
from ..extensions import db
from ..models import Claim, ClaimVerification, Feedback, FoundItem, Handover, LostReport, MatchingResult, utcnow
from ..security import auth_required, can, error, permission_required, rate_limit
from ..utils import audit, clean, notify, paginate
from .items import _staff_ids

bp = Blueprint("claims", __name__, url_prefix="/api")


def locked(model, pk):
    """SELECT ... FOR UPDATE (row lock on MySQL/InnoDB; no-op on SQLite)."""
    return db.session.query(model).filter(model.id == pk).with_for_update().first()


# ---------- submit ----------
@bp.post("/found/<int:fid>/claims")
@permission_required("claims.create")
@rate_limit("claim", 20, 3600)
def submit_claim(fid):
    item = db.session.get(FoundItem, fid)
    if not item or item.status != "available":
        return error("This item is not available for claims.", 404)
    if item.reporter_id == g.user.id:
        return error("You cannot claim an item you registered.", 403)
    p = request.get_json(silent=True) or {}
    description = clean(p.get("description"), 3000)
    if len(description) < 15:
        return error("Validation failed.", 422, fields={"description": "Describe the item in detail (15+ characters): marks, contents, how you lost it."})
    answer = clean(p.get("verification_answer"), 255)
    if item.verification_answer_hash and not answer:
        return error("Validation failed.", 422, fields={"verification_answer": "Please answer the verification question."})

    mine = Claim.query.filter_by(found_item_id=fid, claimant_id=g.user.id).filter(Claim.status != "withdrawn").all()
    if any(c.status == "pending" for c in mine):
        return error("You already have a pending claim for this item.", 409)
    max_attempts = settings_store.get("max_claim_attempts")
    if len(mine) >= max_attempts:
        audit("claim.attempt_limit", g.user, "found_item", fid)
        db.session.commit()
        return error("You have reached the maximum number of claim attempts for this item. Please visit the Lost-and-Found office.", 403)

    lost_id = None
    if p.get("lost_report_id"):
        lr = db.session.get(LostReport, int(p["lost_report_id"])) if str(p["lost_report_id"]).isdigit() else None
        if not lr or lr.user_id != g.user.id:
            return error("Linked lost report not found.", 404)
        lost_id = lr.id

    claim = Claim(found_item_id=fid, claimant_id=g.user.id, description=description, lost_report_id=lost_id)
    db.session.add(claim)
    db.session.flush()
    flags = []
    if item.verification_answer_hash:
        ok = security.answers_match(answer, item.verification_salt, item.verification_answer_hash)
        db.session.add(ClaimVerification(claim_id=claim.id, question=item.verification_question,
                                         submitted_answer_hash=security.hash_answer(answer, item.verification_salt), matched=ok))
        claim.auto_check_passed = ok
        if not ok:
            flags.append("verification answer did not match")
    if any(c.status == "rejected" for c in mine):
        flags.append("previously rejected for this item")
    since = utcnow() - timedelta(hours=24)
    recent = Claim.query.filter(Claim.claimant_id == g.user.id, Claim.created_at >= since).count()
    if recent >= 3:
        flags.append(f"{recent} claims in 24 hours")
    if flags:
        claim.suspicious, claim.flag_reason = True, "; ".join(flags)[:255]
    audit("claim.submit", g.user, "claim", claim.id, found_item_id=fid, suspicious=claim.suspicious)
    for uid in _staff_ids("claims.review"):
        notify(uid, "claim", "New ownership claim", f"A claim was submitted for '{item.title}'." + (" Flagged for review." if claim.suspicious else ""), "/app/admin/manage")
    notify(item.reporter_id, "claim", "Claim on your found item", f"Someone submitted a claim for '{item.title}'. Staff will verify it.", "/app/my-reports")
    db.session.commit()
    # The claimant is intentionally NOT told whether the secret answer matched.
    return jsonify({"claim": claim.to_dict(), "message": "Claim submitted. An officer will verify your details."}), 201


# ---------- list / read ----------
@bp.get("/claims")
@auth_required
def list_claims():
    staff = can("claims.review")
    q = Claim.query
    if not staff:
        q = q.filter(Claim.claimant_id == g.user.id)
    if (s := request.args.get("status")):
        q = q.filter(Claim.status == s)
    if staff and request.args.get("suspicious") == "1":
        q = q.filter(Claim.suspicious.is_(True))
    q = q.order_by(Claim.created_at.desc())
    return jsonify(paginate(q, lambda c: c.to_dict(staff=staff)))


@bp.get("/claims/<int:cid>")
@auth_required
def get_claim(cid):
    c = db.session.get(Claim, cid)
    staff = can("claims.review")
    if not c or (c.claimant_id != g.user.id and not staff):
        return error("Claim not found.", 404)
    return jsonify({"claim": c.to_dict(staff=staff)})


@bp.post("/claims/<int:cid>/withdraw")
@auth_required
def withdraw(cid):
    c = db.session.get(Claim, cid)
    if not c or c.claimant_id != g.user.id:
        return error("Claim not found.", 404)
    if c.status != "pending":
        return error("Only pending claims can be withdrawn.", 409)
    c.status = "withdrawn"
    audit("claim.withdraw", g.user, "claim", c.id, found_item_id=c.found_item_id)
    db.session.commit()
    return jsonify({"claim": c.to_dict()})


# ---------- review (transactional) ----------
@bp.post("/claims/<int:cid>/approve")
@permission_required("claims.review")
@rate_limit("claim_review", 120, 3600)
def approve(cid):
    reason = clean((request.get_json(silent=True) or {}).get("reason"), 500)
    if len(reason) < 5:
        return error("Record how the claimant was verified (min 5 characters).", 422, fields={"reason": "Required"})
    try:
        claim = locked(Claim, cid)
        if not claim:
            return error("Claim not found.", 404)
        item = locked(FoundItem, claim.found_item_id)
        if claim.status != "pending":
            return error("Claim has already been reviewed.", 409)
        if item.status != "available":
            return error("Item is no longer available.", 409)
        if claim.claimant_id == item.reporter_id:
            return error("A reporter cannot receive their own found item via claim.", 409)
        now = utcnow()
        claim.status, claim.reviewed_by, claim.review_reason, claim.reviewed_at = "approved", g.user.id, reason, now
        item.status = "claimed"
        others = Claim.query.filter(Claim.found_item_id == item.id, Claim.id != claim.id, Claim.status == "pending").all()
        for o in others:
            o.status, o.reviewed_by, o.reviewed_at = "rejected", g.user.id, now
            o.review_reason = "Another claim was approved for this item."
            notify(o.claimant_id, "claim", "Claim rejected", f"Your claim for '{item.title}' was not approved: another claim was verified.", "/app/my-claims")
        handover = Handover(claim_id=claim.id, found_item_id=item.id, claimant_id=claim.claimant_id,
                            reference_code=security.new_reference_code())
        db.session.add(handover)
        if claim.lost_report_id:
            lr = db.session.get(LostReport, claim.lost_report_id)
            if lr and lr.status == "open":
                lr.status = "matched"
        MatchingResult.query.filter_by(found_item_id=item.id).delete()
        db.session.flush()
        audit("claim.approve", g.user, "claim", claim.id, found_item_id=item.id, reason=reason)
        notify(claim.claimant_id, "claim", "Claim approved", f"Your claim for '{item.title}' was approved.", "/app/handovers")
        notify(claim.claimant_id, "ready", "Item ready for collection",
               f"Bring your student ID and handover code to the office to collect '{item.title}'." + (f" Location: {item.storage_location}" if item.storage_location else ""), "/app/handovers")
        notify(item.reporter_id, "claim", "Owner verified", f"The owner of '{item.title}' has been verified. Thank you for helping!", "/app/my-reports")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"claim": claim.to_dict(staff=True), "handover_id": handover.id})


@bp.post("/claims/<int:cid>/reject")
@permission_required("claims.review")
def reject(cid):
    reason = clean((request.get_json(silent=True) or {}).get("reason"), 500)
    if len(reason) < 5:
        return error("A rejection reason is required (min 5 characters).", 422, fields={"reason": "Required"})
    claim = locked(Claim, cid)
    if not claim:
        return error("Claim not found.", 404)
    if claim.status != "pending":
        return error("Claim has already been reviewed.", 409)
    claim.status, claim.reviewed_by, claim.review_reason, claim.reviewed_at = "rejected", g.user.id, reason, utcnow()
    audit("claim.reject", g.user, "claim", claim.id, found_item_id=claim.found_item_id, reason=reason)
    notify(claim.claimant_id, "claim", "Claim rejected", f"Your claim for '{claim.item.title}' was not approved. Reason: {reason}", "/app/my-claims")
    db.session.commit()
    return jsonify({"claim": claim.to_dict(staff=True)})


# ---------- handovers ----------
def _handover_dict(h, staff):
    d = {"id": h.id, "status": h.status, "item_id": h.found_item_id, "item_title": h.item.title,
         "item_image": h.item.images[0].url if h.item.images else None,
         "storage_location": h.item.storage_location, "created_at": h.created_at.isoformat(),
         "completed_at": h.completed_at.isoformat() if h.completed_at else None, "id_verified": h.id_verified}
    if staff:
        d["claimant"] = {"name": h.claimant.full_name, "student_id": h.claimant.student_id}
        d["officer"] = h.officer.full_name if h.officer else None
        d["notes"] = h.notes
    else:   # only the claimant ever sees the reference code
        d["reference_code"] = h.reference_code
    return d


@bp.get("/handovers")
@auth_required
def list_handovers():
    staff = can("handovers.manage")
    q = Handover.query
    if not staff:
        q = q.filter(Handover.claimant_id == g.user.id)
    if (s := request.args.get("status")):
        q = q.filter(Handover.status == s)
    return jsonify(paginate(q.order_by(Handover.created_at.desc()), lambda h: _handover_dict(h, staff)))


@bp.post("/handovers/<int:hid>/complete")
@permission_required("handovers.manage")
@rate_limit("handover_complete", 30, 600)
def complete_handover(hid):
    p = request.get_json(silent=True) or {}
    try:
        h = locked(Handover, hid)
        if not h:
            return error("Handover not found.", 404)
        if h.status != "ready":
            return error("This handover is already finished.", 409)
        if not p.get("id_verified"):
            return error("Confirm that the claimant's identity was checked.", 422, fields={"id_verified": "Required"})
        if not security.hmac.compare_digest(str(p.get("reference_code", "")).strip().upper(), h.reference_code):
            audit("handover.code_mismatch", g.user, "handover", h.id, found_item_id=h.found_item_id)
            db.session.commit()
            return error("The handover code does not match.", 400, fields={"reference_code": "Incorrect code"})
        now = utcnow()
        h.status, h.officer_id, h.id_verified, h.completed_at = "completed", g.user.id, True, now
        h.notes = clean(p.get("notes"), 500) or None
        item = locked(FoundItem, h.found_item_id)
        item.status = "returned"
        claim = db.session.get(Claim, h.claim_id)
        if claim.lost_report_id:
            lr = db.session.get(LostReport, claim.lost_report_id)
            if lr:
                lr.status = "recovered"
        audit("handover.complete", g.user, "handover", h.id, found_item_id=item.id, claim_id=claim.id)
        notify(h.claimant_id, "handover", "Handover completed", f"'{item.title}' was returned to you. Please rate your experience.", "/app/handovers")
        notify(item.reporter_id, "handover", "Item returned to owner", f"'{item.title}' that you found has been returned. Thank you!", "/app/my-reports")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"handover": _handover_dict(h, True)})


@bp.get("/handovers/<int:hid>/receipt")
@auth_required
def receipt(hid):
    h = db.session.get(Handover, hid)
    staff = can("handovers.manage")
    if not h or (h.claimant_id != g.user.id and not staff):
        return error("Handover not found.", 404)
    if h.status != "completed":
        return error("Receipt is available after the handover is completed.", 409)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    w, ht = A5
    c.setFont("Helvetica-Bold", 16)
    c.drawString(36, ht - 50, f"{settings_store.get('university_name')} - Lost & Found")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(36, ht - 75, "Handover Receipt")
    c.setFont("Helvetica", 10)
    rows = [("Receipt no.", f"HR-{h.id:06d}"), ("Reference code", h.reference_code), ("Item", h.item.title),
            ("Received by", h.claimant.full_name), ("Student ID", h.claimant.student_id or "-"),
            ("Handed over by", h.officer.full_name if h.officer else "-"),
            ("Date / time (UTC)", h.completed_at.strftime("%Y-%m-%d %H:%M")),
            ("Identity verified", "Yes" if h.id_verified else "No")]
    y = ht - 110
    for k, v in rows:
        c.setFont("Helvetica-Bold", 10); c.drawString(36, y, k + ":")
        c.setFont("Helvetica", 10); c.drawString(150, y, str(v)[:60]); y -= 20
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(36, 50, "Generated by UniFind AI. Keep this receipt as proof of return.")
    c.line(36, 110, 180, 110); c.drawString(36, 98, "Claimant signature")
    c.line(220, 110, 360, 110); c.drawString(220, 98, "Officer signature")
    c.save()
    buf.seek(0)
    audit("handover.receipt", g.user, "handover", h.id)
    db.session.commit()
    return send_file(buf, mimetype="application/pdf", download_name=f"receipt-{h.id}.pdf")


@bp.post("/handovers/<int:hid>/feedback")
@auth_required
def feedback(hid):
    h = db.session.get(Handover, hid)
    if not h or h.claimant_id != g.user.id:
        return error("Handover not found.", 404)
    if h.status != "completed":
        return error("Feedback is available after the handover.", 409)
    if Feedback.query.filter_by(handover_id=hid).first():
        return error("Feedback already submitted.", 409)
    p = request.get_json(silent=True) or {}
    try:
        rating = int(p.get("rating"))
        assert 1 <= rating <= 5
    except (TypeError, ValueError, AssertionError):
        return error("Rating must be between 1 and 5.", 422, fields={"rating": "1-5"})
    db.session.add(Feedback(handover_id=hid, user_id=g.user.id, rating=rating, comment=clean(p.get("comment"), 500) or None))
    audit("feedback.submit", g.user, "handover", hid, rating=rating)
    db.session.commit()
    return jsonify({"message": "Thank you for your feedback."}), 201
