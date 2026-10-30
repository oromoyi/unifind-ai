import json
from datetime import date, timedelta

from app import matching
from app.evaluation import run_evaluation
from app.settings_store import DEFAULTS

W = DEFAULTS["match_weights"]
LOCS = {1: {"id": 1, "x": 0, "y": 0, "zone": "A"}, 2: {"id": 2, "x": 50, "y": 0, "zone": "A"}, 3: {"id": 3, "x": 3000, "y": 0, "zone": "B"}}


def mk(i, cat, text, color, brand, loc, d):
    return dict(id=i, category_id=cat, title=text, description=text, features=None, color=color, brand=brand,
                location_id=loc, date=d, image_paths=[])


def test_scores_are_0_100_and_ranked_sensibly():
    today = date.today()
    lost = mk(1, 1, "black samsung phone cracked screen", "black", "Samsung", 1, today - timedelta(days=2))
    good = mk(10, 1, "samsung smartphone with cracked screen black", "black", "Samsung", 2, today)
    bad = mk(11, 2, "set of brass keys with leather tag", "brown", None, 3, today - timedelta(days=60))
    res = matching.compute_pairs([lost], [good, bad], W, LOCS)
    assert 0 <= res[(1, 11)]["score"] < res[(1, 10)]["score"] <= 100
    assert res[(1, 10)]["score"] > 70
    ex = res[(1, 10)]["explanation"].lower()
    assert "same category" in ex and "colour" in ex
    assert set(res[(1, 10)]["breakdown"]) == {"category", "description", "attributes", "location", "date", "image"}


def test_weights_are_configurable_and_missing_signals_renormalised():
    today = date.today()
    lost = mk(1, 1, "phone", None, None, 1, today)
    found = mk(2, 1, "phone", None, None, 1, today)
    only_cat = matching.compute_pairs([lost], [found], {**W, "description": 0, "location": 0, "date": 0}, LOCS)[(1, 2)]
    assert only_cat["score"] == 100.0
    r = matching.compute_pairs([lost], [found], W, LOCS)[(1, 2)]
    assert r["breakdown"]["image"]["value"] is None and r["breakdown"]["image"]["weight"] == 0


def test_found_before_lost_scores_zero_for_date():
    d = matching.date_score(date(2026, 3, 10), date(2026, 3, 1))
    assert d == 0.0 and matching.date_score(date(2026, 3, 1), date(2026, 3, 1)) == 1.0


def test_color_synonyms():
    assert matching.color_score("navy", "dark blue") == 0.85
    assert matching.color_score("red", "blue") == 0.0
    assert matching.color_score(None, "red") is None


def test_image_similarity_extension_point(tmp_path):
    from PIL import Image
    a, b, c = tmp_path / "a.png", tmp_path / "b.png", tmp_path / "c.png"
    Image.new("RGB", (30, 30), (250, 0, 0)).save(a); Image.new("RGB", (30, 30), (250, 5, 0)).save(b); Image.new("RGB", (30, 30), (0, 0, 250)).save(c)
    assert matching.image_score([str(a)], [str(b)]) > matching.image_score([str(a)], [str(c)])
    assert matching.image_score([], [str(a)]) is None


def test_api_match_flow_and_notification(client, H):
    stu, off = H.login("stu1"), H.login("officer")
    H.found(off)
    r = H.lost(stu)
    m = r.json["matches"]
    assert m and m[0]["score"] >= 60 and m[0]["explanation"]
    notes = client.get("/api/notifications", headers=stu).json
    assert any(n["type"] == "match" for n in notes["items"])
    got = client.get(f"/api/lost/{r.json['report']['id']}/matches", headers=stu).json
    assert "Suggestions only" in got["disclaimer"]
    # a found item registered AFTER the lost report also triggers a match notification
    H.found(off, title="Another black Samsung", description="Black Samsung phone cracked screen protector found outside", confirm_duplicate="1")
    assert len([n for n in client.get("/api/notifications", headers=stu).json["items"] if n["type"] == "match"]) == 2


def test_match_never_changes_item_status(client, H):
    stu, off = H.login("stu1"), H.login("officer")
    fid = H.found(off).json["item"]["id"]
    H.lost(stu)
    assert client.get(f"/api/found/{fid}").json["item"]["status"] == "available"


def test_admin_threshold_changes_results(client, H):
    stu, off, adm = H.login("stu1"), H.login("officer"), H.login("admin")
    H.found(off)
    assert client.put("/api/admin/settings", json={"match_min_score": 99.9}, headers=adm).status_code == 200
    assert H.lost(stu).json["matches"] == []
    assert client.put("/api/admin/settings", json={"match_weights": {"category": -1}}, headers=adm).status_code == 422
    assert client.put("/api/admin/settings", json={"match_min_score": 150}, headers=adm).status_code == 422
    client.put("/api/admin/settings", json={"match_min_score": 30}, headers=adm)
    client.post("/api/admin/rematch", headers=adm)
    assert client.get("/api/matches", headers=stu).json["matches"]


def test_evaluation_runs_on_labelled_dataset(client, H):
    res = run_evaluation(W)
    assert res["dataset"]["synthetic"] is True
    assert res["weighted_matcher"]["mrr"] >= res["baseline_keyword"]["mrr"]     # sanity, not a performance claim
    adm = H.login("admin")
    r = client.get("/api/admin/evaluation", headers=adm).json
    assert r["methodology"] and "baseline_keyword" in r
