import logging
import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config["SECRET_KEY"]:
        if app.config["ENV_NAME"] == "production":
            raise RuntimeError("SECRET_KEY must be set in production.")
        app.config["SECRET_KEY"] = "dev-only-insecure-key-change-me-0123456789"
        logging.getLogger("unifind").warning("SECRET_KEY not set; using an insecure development key.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
         allow_headers=["Content-Type", "Authorization"], supports_credentials=False)
    db.init_app(app)

    from .routes import register_blueprints
    register_blueprints(app)

    @app.get("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(app.config["UPLOAD_DIR"], filename, max_age=3600)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    @app.errorhandler(HTTPException)
    def http_err(e):
        return jsonify({"error": e.description if e.code != 413 else "Upload too large."}), e.code

    from sqlalchemy.exc import OperationalError, ProgrammingError

    @app.errorhandler(OperationalError)
    @app.errorhandler(ProgrammingError)
    def db_err(e):
        logging.getLogger("unifind").error("Database error: %s", e)
        db.session.rollback()
        return jsonify({"error": "Database problem: cannot connect to MySQL or tables are missing. "
                                 "Check backend/.env (DB_USER, DB_PASSWORD, DB_NAME), make sure MySQL is running, "
                                 "then run: python init_db.py --demo"}), 503

    @app.errorhandler(Exception)
    def unhandled(e):
        logging.getLogger("unifind").exception("Unhandled error")
        db.session.rollback()
        return jsonify({"error": "Internal server error."}), 500

    return app
