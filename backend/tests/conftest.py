import io
import os
import shutil
import sys
from datetime import date, timedelta

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Category, Location, Role, User  # noqa: E402
from app.security import hash_password, reset_rate_limits  # noqa: E402
from seed_lib import bootstrap  # noqa: E402


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        bootstrap()
        for email, pw, role, sid in [("admin@t.test", "Admin12345", "admin", None), ("officer@t.test", "Officer12345", "officer", None),
                                     ("stu1@t.test", "Student12345", "student", "UGR/1111/15"), ("stu2@t.test", "Student12345", "student", "UGR/2222/15"),
                                     ("finder@t.test", "Finder12345", "finder", None)]:
            db.session.add(User(email=email, full_name=email.split("@")[0].title(), password_hash=hash_password(pw),
                                role_id=Role.query.filter_by(name=role).one().id, student_id=sid))
        db.session.commit()
        reset_rate_limits()
        yield app
        db.session.remove()
        db.drop_all()
    shutil.rmtree(TestConfig.UPLOAD_DIR, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()


class Helper:
    PW = {"admin": "Admin12345", "officer": "Officer12345", "stu1": "Student12345", "stu2": "Student12345", "finder": "Finder12345"}

    def __init__(self, client, app):
        self.c, self.app = client, app
        with app.app_context():
            self.cat = Category.query.filter_by(name="Phones").one().id
            self.cat2 = Category.query.filter_by(name="Keys").one().id
            self.loc = Location.query.filter_by(name="Main Library").one().id

    def login(self, who):
        r = self.c.post("/api/auth/login", json={"email": f"{who}@t.test", "password": self.PW[who]})
        assert r.status_code == 200, r.json
        return {"Authorization": "Bearer " + r.json["token"]}

    def png(self, color=(200, 30, 30), name="x.png"):
        buf = io.BytesIO(); Image.new("RGB", (40, 40), color).save(buf, "PNG"); buf.seek(0)
        return (buf, name)

    def lost(self, h, **kw):
        d = dict(title="Lost black phone", category_id=self.cat, description="Black Samsung phone with cracked screen protector",
                 color="black", brand="Samsung", location_id=self.loc, date=(date.today() - timedelta(days=2)).isoformat())
        d.update(kw)
        return self.c.post("/api/lost", data=d, headers=h, content_type="multipart/form-data")

    def found(self, h, **kw):
        d = dict(title="Black Samsung phone", category_id=self.cat, description="Black Samsung smartphone with cracked screen protector",
                 color="black", brand="Samsung", location_id=self.loc, date=(date.today() - timedelta(days=1)).isoformat(),
                 verification_question="Lock screen picture?", verification_answer="Red mountain", private_details="Wallpaper: red mountain")
        d.update(kw)
        return self.c.post("/api/found", data=d, headers=h, content_type="multipart/form-data")


@pytest.fixture()
def H(client, app):
    return Helper(client, app)
