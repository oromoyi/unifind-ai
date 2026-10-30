"""Create tables and load DEMO data (all fictional).

  python seed.py            # create tables + bootstrap + demo data (skips if users exist)
  python seed.py --reset    # DROP all tables first, then seed
  python seed.py --bootstrap-only   # roles, permissions, categories, locations only (production)

Demo data is created by calling the real API (so audit logs, matches and notifications are genuine).
Dates are shifted into the past to give the analytics charts something to show; they are demo values.
"""
import io
import os
import random
import sys
from datetime import date, timedelta

from PIL import Image, ImageDraw

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import Feedback, FoundItem, Handover, LostReport, Role, User
from app.security import hash_password
from seed_lib import bootstrap

DEMO_USERS = [  # email, password, name, role, student_id, department
    ("admin@unifind.test", "Admin@12345", "Demo Administrator", "admin", None, "ICT Directorate"),
    ("officer@unifind.test", "Officer@12345", "Demo Security Officer", "officer", None, "Campus Security"),
    ("student1@unifind.test", "Student@12345", "Almaz Tesfaye (demo)", "student", "UGR/1001/15", "Computer Science"),
    ("student2@unifind.test", "Student@12345", "Dawit Bekele (demo)", "student", "UGR/1002/15", "Civil Engineering"),
    ("student3@unifind.test", "Student@12345", "Selam Haile (demo)", "student", "UGR/1003/14", "Medicine"),
    ("finder1@unifind.test", "Finder@12345", "Hanna Girma (demo)", "finder", None, "Business and Economics"),
]
COLOR_RGB = {"black": (35, 35, 40), "blue": (40, 90, 170), "red": (180, 40, 50), "green": (50, 130, 80), "brown": (120, 80, 50),
             "grey": (130, 135, 140), "white": (225, 225, 225), "silver": (170, 175, 180), "navy": (20, 40, 100), "yellow": (220, 180, 40)}


def placeholder(label, color):
    """Illustrative placeholder 'photo' (flat colour + label) - not a real photograph."""
    rgb = COLOR_RGB.get(color, (100, 110, 120))
    im = Image.new("RGB", (480, 360), rgb)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 70, 390, 290), radius=28, outline=(255, 255, 255), width=4)
    d.text((110, 170), label[:30], fill=(255, 255, 255))
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    return buf


def main():
    reset, bootstrap_only = "--reset" in sys.argv, "--bootstrap-only" in sys.argv
    app = create_app(Config)
    with app.app_context():
        if reset:
            db.drop_all()
        db.create_all()
        bootstrap()
        if bootstrap_only:
            print("Bootstrap data ready."); return
        if User.query.count():
            print("Users already exist - skipping demo data (use --reset to rebuild)."); return
        for email, pw, name, role, sid, dept in DEMO_USERS:
            db.session.add(User(email=email, password_hash=hash_password(pw), full_name=name,
                                role_id=Role.query.filter_by(name=role).one().id, student_id=sid, department=dept))
        db.session.commit()
        seed_demo(app)
    print("Seed complete. Demo accounts:")
    for email, pw, name, role, *_ in DEMO_USERS:
        print(f"  {role:8s} {email:26s} {pw}")


def seed_demo(app):
    from app.models import Category, Location
    c = app.test_client()
    cat = {x.name: x.id for x in Category.query.all()}
    loc = {x.name: x.id for x in Location.query.all()}

    def login(email, pw):
        r = c.post("/api/auth/login", json={"email": email, "password": pw}); assert r.status_code == 200, r.json
        return {"Authorization": "Bearer " + r.json["token"]}

    H = {u[3]: login(u[0], u[1]) for u in DEMO_USERS if u[3] in ("admin", "officer", "finder")}
    S = [login(u[0], u[1]) for u in DEMO_USERS if u[3] == "student"]
    today = date.today()

    def post(headers, url, fields, color=None, label=None):
        data = dict(fields, confirm_duplicate="1")
        if label:
            data["images"] = (placeholder(label, color), "photo.png")
        r = c.post(url, data=data, headers=headers, content_type="multipart/form-data")
        assert r.status_code == 201, (url, r.json)
        return r.json

    F = lambda title, cat_, desc, color, brand, loc_, days, **kw: dict(
        title=title, category_id=cat[cat_], description=desc, color=color, brand=brand or "", location_id=loc[loc_],
        date=(today - timedelta(days=days)).isoformat(), **kw)
    found = [
        ("Black Samsung phone", "Phones", "Black Samsung smartphone with a cracked screen protector.", "black", "Samsung", "Main Library", 3,
         dict(verification_question="What is the lock-screen wallpaper?", verification_answer="a red mountain", private_details="Lock screen shows a red mountain.")),
        ("Navy blue backpack", "Bags & Backpacks", "Navy blue Nike backpack with two front pockets.", "navy", "Nike", "Student Cafeteria", 5,
         dict(verification_question="Name one item inside the bag", verification_answer="chemistry textbook")),
        ("Brown leather wallet", "Wallets & Purses", "Brown leather wallet, worn edges, found on a bench.", "brown", "", "Sports Field", 6,
         dict(verification_question="Which bank card is inside?", verification_answer="Dashen")),
        ("Set of keys with football keychain", "Keys", "Three keys on a ring with a football keychain.", "silver", "", "Lecture Hall 1", 2, {}),
        ("Silver HP laptop", "Laptops & Tablets", "Silver HP laptop with stickers on the lid.", "silver", "HP", "Engineering Building", 4,
         dict(verification_question="What sticker is on the lid?", verification_answer="a lion")),
        ("White wireless earbuds", "Electronics & Accessories", "White wireless earbuds in a charging case.", "white", "JBL", "Science Block", 7, {}),
        ("Grey hooded jacket", "Clothing", "Grey zip-up hoodie with small stain on the sleeve.", "grey", "", "Dormitory Block A", 9, {}),
        ("Calculus textbook", "Books & Stationery", "Calculus textbook with highlighted pages and worn spine.", "green", "", "Main Library", 11, {}),
        ("Blue water bottle", "Other", "Blue metal water bottle with a mountain sticker.", "blue", "Hydro Flask", "Student Clinic", 8, {}),
        ("Student ID card holder", "ID Cards & Documents", "ID card in a plastic holder with lanyard.", "yellow", "", "Main Gate", 1, {}),
    ]
    ids = []
    for i, (t, ct, d, col, br, lc, days, extra) in enumerate(found):
        headers = H["officer"] if i % 3 == 0 else H["finder"]
        r = post(headers, "/api/found", F(t, ct, d, col, br, lc, days, **extra), col, t)
        ids.append(r["item"]["id"])
    # officer approves everything the finder registered
    for fid in ids:
        if db.session.get(FoundItem, fid).status == "pending":
            assert c.post(f"/api/found/{fid}/review", json={"decision": "approve"}, headers=H["officer"]).status_code == 200
    lost = [
        (S[0], "Lost my Samsung phone", "Phones", "I lost my black Samsung phone, screen protector is cracked.", "black", "Samsung", "Main Library", 4),
        (S[1], "Missing navy backpack", "Bags & Backpacks", "Navy Nike backpack with two pockets in front, left at the cafeteria.", "navy", "Nike", "Student Cafeteria", 6),
        (S[2], "Lost wallet", "Wallets & Purses", "Brown leather wallet with some cards inside.", "brown", "", "Sports Field", 7),
        (S[0], "Lost HP laptop", "Laptops & Tablets", "Silver HP laptop decorated with stickers.", "silver", "HP", "Engineering Building", 5),
        (S[1], "Lost earphones", "Electronics & Accessories", "White wireless earphones with their case.", "white", "JBL", "Science Block", 8),
    ]
    lost_ids = []
    for hdr, t, ct, d, col, br, lc, days in lost:
        r = post(hdr, "/api/lost", dict(title=t, category_id=cat[ct], description=d, color=col, brand=br, location_id=loc[lc],
                                         date=(today - timedelta(days=days)).isoformat(), distinguishing_features=""), col, t)
        lost_ids.append(r["report"]["id"])
    # claims: student1 recovers the phone (full workflow); student2 gets a flagged wrong-answer claim on the backpack
    def claim(hdr, fid, desc, ans, lost_id=None):
        r = c.post(f"/api/found/{fid}/claims", json=dict(description=desc, verification_answer=ans, lost_report_id=lost_id), headers=hdr)
        assert r.status_code == 201, r.json
        return r.json["claim"]["id"]
    phone_claim = claim(S[0], ids[0], "My phone has a cracked protector and a red mountain wallpaper; bought last year.", "A red mountain", lost_ids[0])
    r = c.post(f"/api/claims/{phone_claim}/approve", json={"reason": "Answer matched, student ID checked at office."}, headers=H["officer"]); assert r.status_code == 200, r.json
    hid = r.json["handover_id"]
    code = c.get("/api/handovers", headers=S[0]).json["items"][0]["reference_code"]
    r = c.post(f"/api/handovers/{hid}/complete", json=dict(reference_code=code, id_verified=True, notes="Collected in person."), headers=H["officer"]); assert r.status_code == 200, r.json
    assert c.post(f"/api/handovers/{hid}/feedback", json=dict(rating=5, comment="Quick and professional."), headers=S[0]).status_code == 201
    claim(S[1], ids[1], "It is my navy backpack, I think it has books inside.", "sandwich", lost_ids[1])      # wrong answer => flagged
    claim(S[2], ids[2], "Brown leather wallet with my bank card and photo of my family inside.", "dashen", lost_ids[2])  # correct => pending review

    # Spread demo dates over the last months so analytics charts have a trend (demo values only).
    rnd = random.Random(7)
    from datetime import datetime
    for f in FoundItem.query.all():
        shift = rnd.randint(0, 120)
        f.created_at = datetime.utcnow() - timedelta(days=shift); f.found_date = f.created_at.date()
    for r in LostReport.query.all():
        shift = rnd.randint(0, 120)
        r.created_at = datetime.utcnow() - timedelta(days=shift); r.lost_date = (r.created_at - timedelta(days=rnd.randint(0, 2))).date()
    for h in Handover.query.filter_by(status="completed").all():
        h.completed_at = h.item.created_at + timedelta(hours=rnd.randint(8, 70)); h.created_at = h.completed_at - timedelta(hours=3)
    db.session.commit()


if __name__ == "__main__":
    main()
