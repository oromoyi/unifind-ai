"""Admin-configurable settings stored in the `settings` table."""
from .extensions import db
from .models import Setting

DEFAULTS = {
    "university_name": "Demo University",
    "departments": ["Computer Science", "Electrical Engineering", "Civil Engineering", "Medicine",
                    "Business and Economics", "Law", "Natural Sciences", "Social Sciences"],
    "student_id_pattern": r"^[A-Za-z]{2,5}/\d{3,6}/\d{2}$",
    "match_weights": {"category": 0.20, "description": 0.30, "attributes": 0.15,
                      "location": 0.15, "date": 0.10, "image": 0.10},
    "match_min_score": 35,       # matches below this are not stored/shown
    "match_notify_score": 60,    # matches at/above this notify the owner
    "match_max_results": 10,
    "max_claim_attempts": 3,
    "blocked_keywords": ["viagra", "casino", "bitcoin"],
}


def get(key):
    row = db.session.get(Setting, key)
    return row.value if row else DEFAULTS[key]


def put(key, value):
    row = db.session.get(Setting, key)
    if row:
        row.value = value
    else:
        db.session.add(Setting(key=key, value=value))


def all_settings():
    return {k: get(k) for k in DEFAULTS}
