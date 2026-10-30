def test_role_permissions(client, H):
    stu, fin, off, adm = H.login("stu1"), H.login("finder"), H.login("officer"), H.login("admin")
    assert H.found(stu).status_code == 403          # students cannot register found items
    assert H.lost(fin).status_code == 403           # finders cannot report lost items
    assert client.get("/api/admin/users", headers=stu).status_code == 403
    assert client.get("/api/admin/users", headers=off).status_code == 403   # officer lacks users.manage
    assert client.get("/api/admin/users", headers=adm).status_code == 200
    assert client.get("/api/admin/audit", headers=off).status_code == 403
    assert client.get("/api/admin/analytics", headers=stu).status_code == 403
    assert client.get("/api/admin/analytics", headers=off).status_code == 200
    assert client.get("/api/admin/analytics").status_code == 401


def test_admin_cannot_demote_self_and_role_edit(client, H):
    adm = H.login("admin")
    me = client.get("/api/auth/me", headers=adm).json["user"]
    assert client.put(f"/api/admin/users/{me['id']}", json={"role": "student"}, headers=adm).status_code == 409
    roles = client.get("/api/admin/roles", headers=adm).json["roles"]
    finder = next(r for r in roles if r["name"] == "finder")
    r = client.put(f"/api/admin/roles/{finder['id']}/permissions", json={"permissions": ["found.create", "lost.create"]}, headers=adm)
    assert r.status_code == 200
    assert H.lost(H.login("finder")).status_code == 201   # new permission effective immediately
    admin_role = next(r for r in roles if r["name"] == "admin")
    assert client.put(f"/api/admin/roles/{admin_role['id']}/permissions", json={"permissions": []}, headers=adm).status_code == 409


def test_users_cannot_read_others_reports_or_claims(client, H):
    s1, s2 = H.login("stu1"), H.login("stu2")
    rid = H.lost(s1).json["report"]["id"]
    assert client.get(f"/api/lost/{rid}", headers=s1).status_code == 200
    assert client.get(f"/api/lost/{rid}", headers=s2).status_code == 404
    assert client.get(f"/api/lost/{rid}/matches", headers=s2).status_code == 404
    assert client.post(f"/api/lost/{rid}/close", headers=s2).status_code == 404


def test_audit_and_user_management(client, H):
    adm = H.login("admin")
    r = client.post("/api/admin/users", json={"full_name": "New Officer", "email": "o2@t.test", "password": "Officer9999", "role": "officer"}, headers=adm)
    assert r.status_code == 201
    logs = client.get("/api/admin/audit?action=admin.user", headers=adm).json["items"]
    assert any(l["action"] == "admin.user_create" for l in logs)
