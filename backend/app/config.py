import os
from dotenv import load_dotenv

load_dotenv()


def _db_uri():
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    from urllib.parse import quote_plus
    return "mysql+pymysql://{u}:{p}@{h}:{port}/{d}?charset=utf8mb4".format(
        u=quote_plus(os.getenv("DB_USER", "unifind")),
        p=quote_plus(os.getenv("DB_PASSWORD", "")),
        h=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "3306"),
        d=os.getenv("DB_NAME", "unifind"),
    )


class Config:
    ENV_NAME = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "8"))
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    UPLOAD_DIR = os.path.abspath(os.getenv("UPLOAD_DIR", "uploads"))
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@unifind.test")
    TESTING = False


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-not-for-production-use-0123456789"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    RATELIMIT_ENABLED = False
    UPLOAD_DIR = os.path.abspath("test_uploads")
