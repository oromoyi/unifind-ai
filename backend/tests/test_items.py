from datetime import date, timedelta


def test_lost_and_found_creation_and_image_upload(client, H):
    stu, fin, off = H.login("stu1"), H.login("finder"), H.login("officer")
    r = H.lost(stu, images=H.png())
    assert r.status_code == 201 and len(r.json["report"]["images"]) == 1
    r = H.found(fin, images=H.png())
    assert r.status_code == 201 and r.json["item"]["status"] == "pending"   # finder items await review
    fid = r.json["item"]["id"]
    assert client.get("/api/found").json["total"] == 0                       # not public yet
    assert client.post(f"/api/found/{fid}/review", json={"decision": "approve"}, headers=fin).status_code == 403
    assert client.post(f"/api/found/{fid}/review", json={"decision": "approve"}, headers=off).status_code == 200
    assert client.get("/api/found").json["total"] == 1
    r = H.found(off, title="Officer item", description="Blue umbrella left at the main gate", category_id=H.cat2, color="blue", brand="")
    assert r.json["item"]["status"] == "available"                           # officer items are published directly


def test_validation_errors(client, H):
    stu = H.login("stu1")
    r = H.lost(stu, title="", description="x", date=(date.today() + timedelta(days=3)).isoformat(), category_id=9999)
    assert r.status_code == 422
    assert {"title", "description", "date", "category_id"} <= set(r.json["fields"])


def test_invalid_uploads_rejected(client, H):
    import io
    stu = H.login("stu1")
    assert H.lost(stu, images=(io.BytesIO(b"<?php echo 1; ?>"), "shell.php")).status_code == 422
    assert H.lost(stu, images=(io.BytesIO(b"not really an image"), "fake.png")).status_code == 422
    assert H.lost(stu, images=(io.BytesIO(b"GIF89a....."), "a.gif")).status_code == 422


def test_public_search_filters_and_no_private_data(client, H):
    off = H.login("officer")
    H.found(off)
    H.found(off, title="Brass keys", description="Set of brass keys with leather tag", category_id=H.cat2, color="brown", brand="", verification_question="", verification_answer="", private_details="engraved ZX9")
    assert client.get("/api/found?q=samsung").json["total"] == 1
    assert client.get("/api/found?q=100%25").json["total"] == 0           # LIKE wildcard is escaped
    assert client.get(f"/api/found?category_id={H.cat2}").json["total"] == 1
    assert client.get("/api/found?color=brown").json["total"] == 1
    assert client.get("/api/found?sort=title").json["items"][0]["title"] == "Black Samsung phone"
    assert client.get("/api/found?q=x';DROP TABLE users;--").status_code == 200   # parameterised queries
    assert client.get("/api/auth/me", headers=H.login("stu1")).status_code == 200  # tables still alive
    body = client.get("/api/found").get_data(as_text=True)
    for secret in ("red mountain", "ZX9", "private_details", "verification_answer", "verification_salt"):
        assert secret.lower() not in body.lower()
    one = client.get("/api/found/1").json["item"]
    assert "private_details" not in one and "verification_question" not in one   # anonymous
    assert client.get("/api/found?page=1&per_page=1").json["pages"] == 2


def test_private_details_visible_only_to_staff_and_reporter(client, H):
    off, fin = H.login("officer"), H.login("finder")
    fid = H.found(fin).json["item"]["id"]
    assert client.get(f"/api/found/{fid}").status_code == 404                       # pending: not public
    assert client.get(f"/api/found/{fid}", headers=H.login("stu1")).status_code == 404
    assert "private_details" in client.get(f"/api/found/{fid}", headers=fin).json["item"]
    client.post(f"/api/found/{fid}/review", json={"decision": "approve"}, headers=off)
    stu_view = client.get(f"/api/found/{fid}", headers=H.login("stu1")).json["item"]
    assert "private_details" not in stu_view and stu_view["verification_question"]


def test_duplicate_detection(client, H):
    stu = H.login("stu1")
    assert H.lost(stu).status_code == 201
    r = H.lost(stu)
    assert r.status_code == 409 and r.json["duplicate"] and r.json["duplicates"][0]["similarity"] >= 80
    assert H.lost(stu, confirm_duplicate="1").status_code == 201
    off = H.login("officer")
    assert H.found(off).status_code == 201
    assert H.found(off).status_code == 409


def test_lost_report_lifecycle(client, H):
    stu, off = H.login("stu1"), H.login("officer")
    rid = H.lost(stu).json["report"]["id"]
    assert client.put(f"/api/lost/{rid}", json={"title": "Lost phone (edited)"}, headers=stu).json["report"]["title"].endswith("(edited)")
    assert client.post(f"/api/lost/{rid}/review", json={"decision": "reject"}, headers=off).status_code == 422   # reason needed
    assert client.post(f"/api/lost/{rid}/review", json={"decision": "reject", "reason": "Spam"}, headers=off).json["report"]["status"] == "rejected"


def test_moderation_keyword_holds_report(client, H):
    r = H.lost(H.login("stu1"), description="Buy bitcoin casino now with my lost phone")
    assert r.json["report"]["status"] == "pending"


def test_lifecycle_timeline_has_no_identities(client, H):
    off = H.login("officer")
    fid = H.found(off).json["item"]["id"]
    t = client.get(f"/api/found/{fid}/timeline").json
    assert t["events"][0]["label"] == "Item registered"
    assert "user" not in str(t).lower()
