"""Authentication (JWT), authorization decorators, rate limiting, hashing helpers."""
import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .models import User


def error(message, status=400, **extra):
    return jsonify({"error": message, **extra}), status


# ---------- passwords ----------
def hash_password(pw):
    return generate_password_hash(pw)


def verify_password(pw, hashed):
    return check_password_hash(hashed, pw)


def password_problem(pw):
    if not isinstance(pw, str) or len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain letters and digits."
    if len(pw) > 128:
        return "Password is too long."
    return None


# ---------- tokens ----------
def create_token(user):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role_name, "iat": now,
               "exp": now + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _load_user_from_request():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        data = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = db.session.get(User, int(data["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    if user is None or not user.is_active:
        return None
    return user


def optional_auth(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        g.user = _load_user_from_request()
        return fn(*a, **kw)
    return wrapper


def auth_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        g.user = _load_user_from_request()
        if g.user is None:
            return error("Authentication required.", 401)
        return fn(*a, **kw)
    return wrapper


def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        @auth_required
        def wrapper(*a, **kw):
            if g.user.role_name not in roles:
                return error("You do not have permission to perform this action.", 403)
            return fn(*a, **kw)
        return wrapper
    return deco


def permission_required(code):
    def deco(fn):
        @wraps(fn)
        @auth_required
        def wrapper(*a, **kw):
            if code not in g.user.permission_codes():
                return error("You do not have permission to perform this action.", 403)
            return fn(*a, **kw)
        return wrapper
    return deco


def can(code):
    return g.user is not None and code in g.user.permission_codes()


# ---------- rate limiting (in-memory sliding window; use Redis for multi-process deployments) ----------
_hits = defaultdict(deque)


def reset_rate_limits():
    _hits.clear()


def rate_limit(name, limit, per_seconds):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if current_app.config.get("RATELIMIT_ENABLED", True):
                key = (name, request.remote_addr or "?")
                now = time.monotonic()
                q = _hits[key]
                while q and now - q[0] > per_seconds:
                    q.popleft()
                if len(q) >= limit:
                    return error("Too many requests. Please try again later.", 429)
                q.append(now)
            return fn(*a, **kw)
        return wrapper
    return deco


# ---------- verification answers: salted, slow hash ----------
def normalise_answer(text):
    text = re.sub(r"[^\w\s]", "", str(text or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def new_salt():
    return secrets.token_hex(16)


def hash_answer(answer, salt):
    return hashlib.pbkdf2_hmac("sha256", normalise_answer(answer).encode(), salt.encode(), 50_000).hex()


def answers_match(answer, salt, stored_hash):
    return hmac.compare_digest(hash_answer(answer, salt), stored_hash or "")


def new_reference_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "UF-" + "".join(secrets.choice(alphabet) for _ in range(8))
