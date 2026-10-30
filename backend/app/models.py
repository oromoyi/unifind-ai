"""Relational model for UniFind AI (MySQL in production, SQLite in tests)."""
from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Stamped:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="joined")


class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), unique=True, nullable=False)
    description = db.Column(db.String(255))


class User(Stamped, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    student_id = db.Column(db.String(40), unique=True)
    department = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    role = db.relationship("Role", lazy="joined")

    @property
    def role_name(self):
        return self.role.name

    def permission_codes(self):
        return {p.code for p in self.role.permissions}

    def to_public(self):
        return {"id": self.id, "full_name": self.full_name, "email": self.email, "role": self.role_name,
                "student_id": self.student_id, "department": self.department, "phone": self.phone,
                "permissions": sorted(self.permission_codes())}

    def to_admin(self):
        d = self.to_public()
        d.update(is_active=self.is_active, created_at=self.created_at.isoformat(),
                 last_login=self.last_login.isoformat() if self.last_login else None)
        return d


class Category(db.Model):
    __tablename__ = "item_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "is_active": self.is_active}


class Location(db.Model):
    __tablename__ = "campus_locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    zone = db.Column(db.String(60))
    x = db.Column(db.Float)  # metres on an arbitrary campus grid (used for proximity)
    y = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "zone": self.zone, "x": self.x, "y": self.y,
                "is_active": self.is_active}


class LostReport(Stamped, db.Model):
    __tablename__ = "lost_reports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("item_categories.id"), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(40))
    brand = db.Column(db.String(60))
    distinguishing_features = db.Column(db.Text)
    location_id = db.Column(db.Integer, db.ForeignKey("campus_locations.id"), nullable=False)
    lost_date = db.Column(db.Date, nullable=False, index=True)
    # pending | open | matched | recovered | closed | rejected | archived
    status = db.Column(db.String(20), default="open", nullable=False, index=True)
    status_reason = db.Column(db.String(255))
    user = db.relationship("User", lazy="joined")
    category = db.relationship("Category", lazy="joined")
    location = db.relationship("Location", lazy="joined")
    images = db.relationship("ItemImage", lazy="selectin")

    def to_dict(self, owner=True):
        return {"id": self.id, "kind": "lost", "title": self.title, "category": self.category.name,
                "category_id": self.category_id, "description": self.description, "color": self.color,
                "brand": self.brand, "distinguishing_features": self.distinguishing_features,
                "location": self.location.name, "location_id": self.location_id,
                "date": self.lost_date.isoformat(), "status": self.status, "status_reason": self.status_reason,
                "images": [i.url for i in self.images], "created_at": self.created_at.isoformat(),
                "reporter": {"id": self.user.id, "name": self.user.full_name} if owner else None}


class FoundItem(Stamped, db.Model):
    __tablename__ = "found_items"
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("item_categories.id"), nullable=False, index=True)
    public_description = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(40))
    brand = db.Column(db.String(60))
    # PRIVATE: never serialised for the public
    private_details = db.Column(db.Text)
    verification_question = db.Column(db.String(255))
    verification_salt = db.Column(db.String(64))
    verification_answer_hash = db.Column(db.String(128))
    location_id = db.Column(db.Integer, db.ForeignKey("campus_locations.id"), nullable=False)
    found_date = db.Column(db.Date, nullable=False, index=True)
    storage_location = db.Column(db.String(150))  # where the item is physically kept
    # pending | available | claimed | returned | rejected | archived
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    status_reason = db.Column(db.String(255))
    reporter = db.relationship("User", lazy="joined")
    category = db.relationship("Category", lazy="joined")
    location = db.relationship("Location", lazy="joined")
    images = db.relationship("ItemImage", lazy="selectin")

    def to_public(self):
        return {"id": self.id, "kind": "found", "title": self.title, "category": self.category.name,
                "category_id": self.category_id, "description": self.public_description, "color": self.color,
                "brand": self.brand, "location": self.location.name, "location_id": self.location_id,
                "date": self.found_date.isoformat(), "status": self.status,
                "has_verification": bool(self.verification_answer_hash),
                "images": [i.url for i in self.images], "created_at": self.created_at.isoformat()}

    def to_private(self):
        d = self.to_public()
        d.update(private_details=self.private_details, verification_question=self.verification_question,
                 storage_location=self.storage_location, status_reason=self.status_reason,
                 reporter={"id": self.reporter.id, "name": self.reporter.full_name})
        return d


class ItemImage(db.Model):
    __tablename__ = "item_images"
    id = db.Column(db.Integer, primary_key=True)
    found_item_id = db.Column(db.Integer, db.ForeignKey("found_items.id", ondelete="CASCADE"), index=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey("lost_reports.id", ondelete="CASCADE"), index=True)
    filename = db.Column(db.String(190), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @property
    def url(self):
        from flask import current_app
        base = current_app.config.get("S3_PUBLIC_BASE_URL")
        return f"{base}/{self.filename}" if base else f"/uploads/{self.filename}"


class Claim(Stamped, db.Model):
    __tablename__ = "claims"
    id = db.Column(db.Integer, primary_key=True)
    found_item_id = db.Column(db.Integer, db.ForeignKey("found_items.id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey("lost_reports.id"))
    description = db.Column(db.Text, nullable=False)  # claimant's private proof of ownership
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)  # pending|approved|rejected|withdrawn
    auto_check_passed = db.Column(db.Boolean)
    suspicious = db.Column(db.Boolean, default=False, nullable=False)
    flag_reason = db.Column(db.String(255))
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    review_reason = db.Column(db.String(500))
    reviewed_at = db.Column(db.DateTime)
    item = db.relationship("FoundItem", lazy="joined")
    claimant = db.relationship("User", foreign_keys=[claimant_id], lazy="joined")
    verifications = db.relationship("ClaimVerification", lazy="selectin")
    handover = db.relationship("Handover", uselist=False, lazy="joined")

    def to_dict(self, staff=False):
        d = {"id": self.id, "found_item_id": self.found_item_id, "item_title": self.item.title,
             "item_image": self.item.images[0].url if self.item.images else None,
             "status": self.status, "created_at": self.created_at.isoformat(),
             "review_reason": self.review_reason,
             "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
             "handover": {"id": self.handover.id, "reference_code": self.handover.reference_code,
                          "status": self.handover.status} if self.handover and not staff else None}
        if staff:
            d.update(description=self.description, suspicious=self.suspicious, flag_reason=self.flag_reason,
                     auto_check_passed=self.auto_check_passed, lost_report_id=self.lost_report_id,
                     claimant={"id": self.claimant.id, "name": self.claimant.full_name,
                               "email": self.claimant.email, "student_id": self.claimant.student_id,
                               "phone": self.claimant.phone},
                     verification_question=self.item.verification_question,
                     private_details=self.item.private_details,
                     handover_id=self.handover.id if self.handover else None)
        else:
            d["description"] = self.description
        return d


class ClaimVerification(db.Model):
    __tablename__ = "claim_verifications"
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    question = db.Column(db.String(255), nullable=False)
    submitted_answer_hash = db.Column(db.String(128), nullable=False)  # salted hash, never plaintext
    matched = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Handover(db.Model):
    __tablename__ = "handovers"
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey("claims.id"), unique=True, nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey("found_items.id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    reference_code = db.Column(db.String(24), unique=True, nullable=False)
    status = db.Column(db.String(20), default="ready", nullable=False, index=True)  # ready|completed|cancelled
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    id_verified = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    item = db.relationship("FoundItem", lazy="joined")
    claimant = db.relationship("User", foreign_keys=[claimant_id], lazy="joined")
    officer = db.relationship("User", foreign_keys=[officer_id], lazy="joined")


class Feedback(db.Model):
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    handover_id = db.Column(db.Integer, db.ForeignKey("handovers.id"), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(190))
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    __table_args__ = (db.Index("ix_notif_user_read", "user_id", "is_read"),)

    def to_dict(self):
        return {"id": self.id, "type": self.type, "title": self.title, "message": self.message,
                "link": self.link, "is_read": self.is_read, "created_at": self.created_at.isoformat()}


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    entity_type = db.Column(db.String(40), index=True)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    user = db.relationship("User", lazy="joined")

    def to_dict(self):
        return {"id": self.id, "user": self.user.full_name if self.user else None, "action": self.action,
                "entity_type": self.entity_type, "entity_id": self.entity_id, "details": self.details,
                "ip_address": self.ip_address, "created_at": self.created_at.isoformat()}


class MatchingResult(db.Model):
    __tablename__ = "matching_results"
    id = db.Column(db.Integer, primary_key=True)
    lost_report_id = db.Column(db.Integer, db.ForeignKey("lost_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    found_item_id = db.Column(db.Integer, db.ForeignKey("found_items.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    breakdown = db.Column(db.JSON)
    explanation = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint("lost_report_id", "found_item_id", name="uq_match_pair"),)
    found_item = db.relationship("FoundItem", lazy="joined")
    lost_report = db.relationship("LostReport", lazy="joined")


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.JSON, nullable=False)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
