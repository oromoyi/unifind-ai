"""Idempotent bootstrap data: roles, permissions, categories, locations. Used by seed.py and tests."""
from app.extensions import db
from app.models import Category, Location, Permission, Role
from app.security import hash_password

PERMISSIONS = {
    "lost.create": "Create lost-item reports", "found.create": "Register found items",
    "claims.create": "Submit ownership claims", "items.review": "Approve/reject/archive item reports",
    "claims.review": "Review ownership claims", "handovers.manage": "Record physical handovers",
    "users.manage": "Manage users", "roles.manage": "Manage role permissions",
    "settings.manage": "Manage catalogue, matching and moderation settings",
    "audit.view": "View audit logs", "analytics.view": "View analytics and evaluation", "reports.export": "Export CSV/PDF reports",
}
ROLES = {
    "student": ("Student / staff member who lost an item", ["lost.create", "claims.create"]),
    "finder": ("Person who found an item", ["found.create"]),
    "officer": ("Security / lost-and-found officer", ["found.create", "items.review", "claims.review", "handovers.manage", "analytics.view"]),
    "admin": ("System administrator", list(PERMISSIONS)),
}
CATEGORIES = ["Phones", "Laptops & Tablets", "Wallets & Purses", "Keys", "Bags & Backpacks", "ID Cards & Documents",
              "Electronics & Accessories", "Clothing", "Books & Stationery", "Other"]
LOCATIONS = [("Main Library", "Central", 0, 0), ("Student Cafeteria", "Central", 120, 60), ("Engineering Building", "North", 50, 400),
             ("Science Block", "North", 150, 450), ("Dormitory Block A", "East", 700, 100), ("Dormitory Block B", "East", 760, 160),
             ("Sports Field", "South", 300, -500), ("Main Gate", "West", -600, 0), ("Lecture Hall 1", "Central", -40, 80),
             ("Student Clinic", "East", 500, -100), ("Administration Building", "Central", -150, -120)]


def bootstrap():
    perms = {}
    for code, desc in PERMISSIONS.items():
        p = Permission.query.filter_by(code=code).first() or Permission(code=code, description=desc)
        db.session.add(p); perms[code] = p
    for name, (desc, codes) in ROLES.items():
        r = Role.query.filter_by(name=name).first()
        if not r:
            r = Role(name=name, description=desc); db.session.add(r)
            r.permissions = [perms[c] for c in codes]   # only set for new roles: admin edits persist
    for n in CATEGORIES:
        if not Category.query.filter_by(name=n).first():
            db.session.add(Category(name=n))
    for n, z, x, y in LOCATIONS:
        if not Location.query.filter_by(name=n).first():
            db.session.add(Location(name=n, zone=z, x=x, y=y))
    db.session.commit()
