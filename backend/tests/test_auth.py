def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"full_name": "New Student", "email": "new@t.test", "password": "Secret1234",
                                                "student_id": "UGR/3333/15", "role": "student"})
    assert r.status_code == 201 and r.json["user"]["role"] == "student"
    assert "password" not in str(r.json)
    r = client.post("/api/auth/login", json={"email": "NEW@t.test", "password": "Secret1234"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + r.json["token"]})
    assert me.json["user"]["email"] == "new@t.test"


def test_cannot_self_register_privileged_roles(client):
    for role in ("admin", "officer"):
        r = client.post("/api/auth/register", json={"full_name": "Evil", "email": f"{role}@evil.test", "password": "Secret1234", "role": role})
        assert r.status_code == 422 and "role" in r.json["fields"]


def test_validation_and_duplicates(client):
    assert client.post("/api/auth/register", json={"full_name": "A", "email": "bad", "password": "short", "role": "student"}).status_code == 422
    r = client.post("/api/auth/register", json={"full_name": "Dup", "email": "stu1@t.test", "password": "Secret1234", "student_id": "UGR/4444/15"})
    assert r.status_code == 422 and "email" in r.json["fields"]
    r = client.post("/api/auth/register", json={"full_name": "Bad Id", "email": "x@t.test", "password": "Secret1234", "student_id": "123"})
    assert "student_id" in r.json["fields"]


def test_wrong_password_and_lockout(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "stu1@t.test", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "stu1@t.test", "password": "Student12345"}).status_code == 423


def test_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_login_rate_limit(app, client):
    app.config["RATELIMIT_ENABLED"] = True
    codes = [client.post("/api/auth/login", json={"email": "nobody@t.test", "password": "x"}).status_code for _ in range(17)]
    assert 429 in codes


def test_deactivated_user_token_rejected(client, H):
    h = H.login("stu1")
    from app.models import User
    from app.extensions import db
    with client.application.app_context():
        User.query.filter_by(email="stu1@t.test").one().is_active = False
        db.session.commit()
    assert client.get("/api/auth/me", headers=h).status_code == 401
