import re
from datetime import timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from .. import settings_store
from ..extensions import db
from ..models import Role, User, utcnow
from ..security import (auth_required, create_token, error, hash_password, password_problem,
                        rate_limit, verify_password)
from ..utils import audit, clean, get_payload

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PUBLIC_ROLES = {"student", "finder"}   # administrators/officers can never self-register
MAX_FAILED, LOCK_MINUTES = 5, 15


@bp.post("/register")
@rate_limit("register", 10, 3600)
def register():
    p = request.get_json(silent=True) or {}
    name, email = clean(p.get("full_name"), 120), clean(p.get("email"), 190).lower()
    role_name = clean(p.get("role")) or "student"
    errs = {}
    if len(name) < 2:
        errs["full_name"] = "Full name is required."
    if not EMAIL_RE.match(email):
        errs["email"] = "Enter a valid email address."
    if (m := password_problem(p.get("password"))):
        errs["password"] = m
    if role_name not in PUBLIC_ROLES:
        errs["role"] = "Invalid role. Only student or finder accounts can be self-registered."
    sid = clean(p.get("student_id"), 40) or None
    if role_name == "student" and not sid:
        errs["student_id"] = "Student ID is required for students."
    if sid and not re.match(settings_store.get("student_id_pattern"), sid):
        errs["student_id"] = "Student ID format is invalid (example: UGR/1234/15)."
    if "password" not in errs and p.get("password") != p.get("confirm_password", p.get("password")):
        errs["confirm_password"] = "Passwords do not match."
    if errs:
        return error("Validation failed.", 422, fields=errs)
    if User.query.filter(func.lower(User.email) == email).first():
        return error("Validation failed.", 422, fields={"email": "This email is already registered."})
    if sid and User.query.filter_by(student_id=sid).first():
        return error("Validation failed.", 422, fields={"student_id": "This student ID is already registered."})
    role = Role.query.filter_by(name=role_name).one()
    user = User(full_name=name, email=email, password_hash=hash_password(p["password"]), role_id=role.id,
                student_id=sid, department=clean(p.get("department"), 120) or None,
                phone=clean(p.get("phone"), 30) or None)
    db.session.add(user)
    db.session.flush()
    audit("user.register", user, "user", user.id, role=role_name)
    db.session.commit()
    return jsonify({"token": create_token(user), "user": user.to_public()}), 201


@bp.post("/login")
@rate_limit("login", 15, 300)
def login():
    p = request.get_json(silent=True) or {}
    email = clean(p.get("email"), 190).lower()
    user = User.query.filter(func.lower(User.email) == email).first()
    generic = "Invalid email or password."
    if user and user.locked_until and user.locked_until > utcnow():
        audit("user.login_blocked", user, "user", user.id)
        db.session.commit()
        return error("Account temporarily locked after repeated failed logins. Try again later.", 423)
    if not user or not verify_password(str(p.get("password") or ""), user.password_hash):
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED:
                user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
                user.failed_logins = 0
            audit("user.login_failed", user, "user", user.id)
            db.session.commit()
        return error(generic, 401)
    if not user.is_active:
        return error("This account has been deactivated.", 403)
    user.failed_logins, user.locked_until, user.last_login = 0, None, utcnow()
    audit("user.login", user, "user", user.id)
    db.session.commit()
    return jsonify({"token": create_token(user), "user": user.to_public()})


@bp.get("/me")
@auth_required
def me():
    return jsonify({"user": g.user.to_public()})


@bp.put("/me")
@auth_required
def update_me():
    p = request.get_json(silent=True) or {}
    u = g.user
    if "full_name" in p and len(clean(p["full_name"])) >= 2:
        u.full_name = clean(p["full_name"], 120)
    if "department" in p:
        u.department = clean(p["department"], 120) or None
    if "phone" in p:
        u.phone = clean(p["phone"], 30) or None
    audit("user.update_profile", u, "user", u.id)
    db.session.commit()
    return jsonify({"user": u.to_public()})


@bp.post("/change-password")
@auth_required
@rate_limit("chpw", 10, 600)
def change_password():
    p = request.get_json(silent=True) or {}
    if not verify_password(str(p.get("current_password") or ""), g.user.password_hash):
        return error("Current password is incorrect.", 400)
    if (m := password_problem(p.get("new_password"))):
        return error(m, 422, fields={"new_password": m})
    g.user.password_hash = hash_password(p["new_password"])
    audit("user.change_password", g.user, "user", g.user.id)
    db.session.commit()
    return jsonify({"message": "Password updated."})
