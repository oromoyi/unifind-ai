def setup_item(client, H, **kw):
    off = H.login("officer")
    fid = H.found(off, **kw).json["item"]["id"]
    return off, fid


def claim(client, h, fid, answer="red mountain", desc="My phone, bought last year, with a red mountain wallpaper and cracked protector.", **kw):
    return client.post(f"/api/found/{fid}/claims", json=dict(description=desc, verification_answer=answer, **kw), headers=h)


def test_claim_correct_answer_not_flagged_and_hash_only(client, app, H):
    off, fid = setup_item(client, H)
    s1 = H.login("stu1")
    r = claim(client, s1, fid, answer="  Red Mountain! ")
    assert r.status_code == 201 and "auto_check" not in str(r.json) and "matched" not in str(r.json)
    from app.models import Claim, ClaimVerification, FoundItem
    with app.app_context():
        c = Claim.query.one()
        assert c.auto_check_passed is True and c.suspicious is False
        v = ClaimVerification.query.one()
        assert "mountain" not in v.submitted_answer_hash and len(v.submitted_answer_hash) == 64
        item = FoundItem.query.one()
        assert "mountain" not in item.verification_answer_hash and item.verification_salt
    staff = client.get("/api/claims", headers=off).json["items"][0]
    assert staff["auto_check_passed"] is True and staff["claimant"]["student_id"] == "UGR/1111/15"


def test_wrong_answer_flagged_and_attempts_limited(client, H):
    off, fid = setup_item(client, H)
    s1 = H.login("stu1")
    r = claim(client, s1, fid, answer="blue sea")
    assert r.status_code == 201
    assert claim(client, s1, fid).status_code == 409                       # pending claim already exists
    cid = r.json["claim"]["id"]
    flagged = client.get(f"/api/claims/{cid}", headers=off).json["claim"]
    assert flagged["suspicious"] and "did not match" in flagged["flag_reason"]
    assert client.get("/api/claims?suspicious=1", headers=off).json["total"] == 1
    client.post(f"/api/claims/{cid}/reject", json={"reason": "Answer incorrect"}, headers=off)
    assert claim(client, s1, fid, answer="nope").status_code == 201
    client.post(f"/api/claims/2/reject", json={"reason": "Answer incorrect"}, headers=off)
    assert claim(client, s1, fid, answer="again").status_code == 201
    client.post(f"/api/claims/3/reject", json={"reason": "Answer incorrect"}, headers=off)
    r = claim(client, s1, fid)
    assert r.status_code == 403 and "maximum" in r.json["error"]


def test_claimant_view_hides_verification_data(client, H):
    off, fid = setup_item(client, H)
    s1 = H.login("stu1")
    cid = claim(client, s1, fid).json["claim"]["id"]
    body = client.get(f"/api/claims/{cid}", headers=s1).get_data(as_text=True).lower()
    for hidden in ("suspicious", "flag_reason", "private_details", "red mountain wallpaper\"", "student_id"):
        assert hidden not in body.replace("my phone, bought last year, with a red mountain wallpaper", "")
    assert client.get(f"/api/claims/{cid}", headers=H.login("stu2")).status_code == 404


def test_cannot_claim_own_or_unavailable_items(client, H):
    fin = H.login("finder")
    fid = H.found(fin).json["item"]["id"]
    assert claim(client, H.login("stu1"), fid).status_code == 404            # still pending review
    assert claim(client, H.login("officer"), fid).status_code == 403         # officers have no claims.create
    assert claim(client, fin, fid).status_code == 403


def test_short_description_rejected(client, H):
    off, fid = setup_item(client, H)
    r = claim(client, H.login("stu1"), fid, desc="mine")
    assert r.status_code == 422 and "description" in r.json["fields"]


def test_full_workflow_approve_handover_receipt_feedback(client, app, H):
    off, fid = setup_item(client, H)
    s1, s2 = H.login("stu1"), H.login("stu2")
    lost_id = H.lost(s1).json["report"]["id"]
    c1 = claim(client, s1, fid, lost_report_id=lost_id).json["claim"]["id"]
    c2 = claim(client, s2, fid, answer="red mountain").json["claim"]["id"]
    assert client.post(f"/api/claims/{c1}/approve", json={"reason": ""}, headers=off).status_code == 422
    assert client.post(f"/api/claims/{c1}/approve", json={"reason": "ID and answer verified"}, headers=s1).status_code == 403
    r = client.post(f"/api/claims/{c1}/approve", json={"reason": "ID and answer verified"}, headers=off)
    assert r.status_code == 200
    hid = r.json["handover_id"]
    assert client.get(f"/api/claims/{c2}", headers=off).json["claim"]["status"] == "rejected"   # competing claim closed
    assert client.post(f"/api/claims/{c1}/approve", json={"reason": "again again"}, headers=off).status_code == 409
    assert client.get(f"/api/found/{fid}").status_code == 404                                       # no longer public
    # claimant sees the code, staff list does not
    mine = client.get("/api/handovers", headers=s1).json["items"][0]
    code = mine["reference_code"]
    assert "reference_code" not in client.get("/api/handovers", headers=off).json["items"][0]
    assert client.post(f"/api/handovers/{hid}/complete", json={"reference_code": "UF-WRONG000", "id_verified": True}, headers=off).status_code == 400
    assert client.post(f"/api/handovers/{hid}/complete", json={"reference_code": code}, headers=off).status_code == 422   # id check required
    assert client.post(f"/api/handovers/{hid}/complete", json={"reference_code": code, "id_verified": True}, headers=s1).status_code == 403
    assert client.get(f"/api/handovers/{hid}/receipt", headers=s1).status_code == 409           # not completed yet
    assert client.post(f"/api/handovers/{hid}/complete", json={"reference_code": code.lower(), "id_verified": True, "notes": "ok"}, headers=off).status_code == 200
    assert client.post(f"/api/handovers/{hid}/complete", json={"reference_code": code, "id_verified": True}, headers=off).status_code == 409
    pdf = client.get(f"/api/handovers/{hid}/receipt", headers=s1)
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
    assert client.get(f"/api/handovers/{hid}/receipt", headers=s2).status_code == 404
    assert client.get(f"/api/lost/{lost_id}", headers=s1).json["report"]["status"] == "recovered"
    assert client.post(f"/api/handovers/{hid}/feedback", json={"rating": 9}, headers=s1).status_code == 422
    assert client.post(f"/api/handovers/{hid}/feedback", json={"rating": 5, "comment": "great"}, headers=s1).status_code == 201
    assert client.post(f"/api/handovers/{hid}/feedback", json={"rating": 5}, headers=s1).status_code == 409
    kinds = [n["type"] for n in client.get("/api/notifications", headers=s1).json["items"]]
    assert {"claim", "ready", "handover"} <= set(kinds)
    adm = H.login("admin")
    k = client.get("/api/admin/analytics", headers=adm).json["kpis"]
    assert k["returned_items"] == 1 and k["avg_time_to_recovery_hours"] is not None and k["avg_feedback_rating"] == 5
    tl = [e["label"] for e in client.get(f"/api/found/{fid}/timeline", headers=s1).json["events"]]
    assert "Handed over to the verified owner" in tl


def test_audit_log_entries_for_workflow(client, H):
    off, fid = setup_item(client, H)
    s1 = H.login("stu1")
    cid = claim(client, s1, fid).json["claim"]["id"]
    client.post(f"/api/claims/{cid}/approve", json={"reason": "verified in person"}, headers=off)
    actions = [l["action"] for l in client.get("/api/admin/audit?per_page=100", headers=H.login("admin")).json["items"]]
    for a in ("found.create", "claim.submit", "claim.approve", "user.login"):
        assert a in actions
    entry = next(l for l in client.get("/api/admin/audit", headers=H.login("admin")).json["items"] if l["action"] == "claim.approve")
    assert entry["details"]["reason"] == "verified in person" and entry["user"]


def test_reject_requires_reason_and_notifies(client, H):
    off, fid = setup_item(client, H)
    s1 = H.login("stu1")
    cid = claim(client, s1, fid).json["claim"]["id"]
    assert client.post(f"/api/claims/{cid}/reject", json={}, headers=off).status_code == 422
    assert client.post(f"/api/claims/{cid}/reject", json={"reason": "Details do not match"}, headers=off).status_code == 200
    n = client.get("/api/notifications", headers=s1).json["items"][0]
    assert "Details do not match" in n["message"]


def test_approval_rolls_back_on_failure(client, app, H, monkeypatch):
    from app.extensions import db
    off, fid = setup_item(client, H)
    cid = claim(client, H.login("stu1"), fid).json["claim"]["id"]
    from app.routes import claims as mod
    monkeypatch.setattr(mod.security, "new_reference_code", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert client.post(f"/api/claims/{cid}/approve", json={"reason": "verified ok"}, headers=off).status_code == 500
    from app.models import Claim, FoundItem
    with app.app_context():
        assert db.session.get(Claim, cid).status == "pending" and db.session.get(FoundItem, fid).status == "available"


def test_notifications_api(client, H):
    stu, off = H.login("stu1"), H.login("officer")
    H.found(off); H.lost(stu)
    n = client.get("/api/notifications", headers=stu).json
    assert n["unread"] >= 1
    nid = n["items"][0]["id"]
    assert client.post(f"/api/notifications/{nid}/read", headers=H.login("stu2")).status_code == 404
    assert client.post(f"/api/notifications/{nid}/read", headers=stu).status_code == 200
    client.post("/api/notifications/read-all", headers=stu)
    assert client.get("/api/notifications/unread-count", headers=stu).json["unread"] == 0


def test_exports_csv_pdf_and_injection_guard(client, H):
    off, adm = H.login("officer"), H.login("admin")
    H.found(off, title="=HYPERLINK(\"http://evil\")")
    r = client.get("/api/admin/export/found-items?format=csv", headers=adm)
    assert r.status_code == 200 and "'=HYPERLINK" in r.get_data(as_text=True)
    assert client.get("/api/admin/export/summary?format=pdf", headers=adm).data[:4] == b"%PDF"
    assert client.get("/api/admin/export/found-items", headers=off).status_code == 403
    assert client.get("/api/admin/export/nothing", headers=adm).status_code == 404
