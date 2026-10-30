"""Helpers: audit trail, notifications (+optional SMTP), pagination, uploads, validation."""
import io
import logging
import os
import smtplib
import uuid
from email.message import EmailMessage

from flask import current_app, request
from PIL import Image, UnidentifiedImageError

from .extensions import db
from .models import AuditLog, ItemImage, Notification, User

log = logging.getLogger("unifind")
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}


def audit(action, user=None, entity_type=None, entity_id=None, **details):
    """Add an audit row to the current session (committed with the caller's transaction)."""
    db.session.add(AuditLog(user_id=user.id if user else None, action=action, entity_type=entity_type,
                            entity_id=entity_id, details=details or None,
                            ip_address=(request.remote_addr if request else None)))


def notify(user_id, type_, title, message, link=None):
    db.session.add(Notification(user_id=user_id, type=type_, title=title, message=message[:500], link=link))
    _maybe_email(user_id, title, message)


def _maybe_email(user_id, subject, body):
    cfg = current_app.config
    if not cfg.get("SMTP_HOST") or cfg.get("TESTING"):
        return
    user = db.session.get(User, user_id)
    if not user:
        return
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = f"[UniFind AI] {subject}", cfg["SMTP_FROM"], user.email
        msg.set_content(body)
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as s:
            s.starttls()
            if cfg["SMTP_USER"]:
                s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
    except Exception:  # email must never break the workflow
        log.exception("email delivery failed")


def paginate(query, serializer, default_per_page=12):
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", default_per_page))))
    except ValueError:
        page, per_page = 1, default_per_page
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": [serializer(i) for i in p.items], "page": p.page, "pages": p.pages or 1,
            "total": p.total, "per_page": per_page}


def clean(text, max_len=None):
    text = (text or "").strip() if isinstance(text, str) else ""
    return text[:max_len] if max_len else text


def get_payload():
    """Accept JSON or multipart form data."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


# ---------- uploads ----------
class UploadError(ValueError):
    pass


def validate_image(file_storage):
    """Check extension, size and that the bytes really are a decodable image. Returns (bytes, ext)."""
    name = (file_storage.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise UploadError("Only JPG, PNG or WEBP images are allowed.")
    raw = file_storage.read()
    if len(raw) > current_app.config["MAX_UPLOAD_MB"] * 1024 * 1024:
        raise UploadError(f"Image is larger than {current_app.config['MAX_UPLOAD_MB']} MB.")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise UploadError("File is not a valid image.")
    if fmt not in ALLOWED_FORMATS:
        raise UploadError("Unsupported image format.")
    if img.width * img.height > 40_000_000:
        raise UploadError("Image dimensions are too large.")
    # Re-encode: strips EXIF/GPS metadata and any appended payload.
    out = io.BytesIO()
    img = img.convert("RGB") if fmt == "JPEG" else img
    img.thumbnail((1600, 1600))
    img.save(out, format=fmt)
    return out.getvalue(), ALLOWED_FORMATS[fmt]


def store_image(data, ext):
    filename = f"{uuid.uuid4().hex}.{ext}"
    if current_app.config["STORAGE_BACKEND"] == "s3":
        import boto3  # optional dependency: pip install boto3
        boto3.client("s3", region_name=os.getenv("S3_REGION")).put_object(
            Bucket=os.environ["S3_BUCKET"], Key=filename, Body=data, ContentType=f"image/{ext}")
    else:
        os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)
        with open(os.path.join(current_app.config["UPLOAD_DIR"], filename), "wb") as fh:
            fh.write(data)
    return filename


def save_uploads(files, **owner):
    """Validate every file first, then store. owner = found_item_id=.. or lost_report_id=.."""
    prepared = [validate_image(f) for f in files if f and f.filename][:4]
    for data, ext in prepared:
        db.session.add(ItemImage(filename=store_image(data, ext), **owner))
    return len(prepared)


def local_image_paths(images):
    if current_app.config["STORAGE_BACKEND"] != "local":
        return []
    return [os.path.join(current_app.config["UPLOAD_DIR"], i.filename) for i in images]
