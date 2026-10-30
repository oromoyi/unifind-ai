import logging
import os

from app import create_app
from app.config import Config
from app.extensions import db

app = create_app(Config)


def ensure_tables():
    """Create missing tables and reference data automatically so a fresh database just works."""
    try:
        with app.app_context():
            db.create_all()
            from seed_lib import bootstrap
            bootstrap()
    except Exception as e:  # keep the server up; API answers with a clear 503 message
        logging.getLogger("unifind").error(
            "\n*** Could not prepare the database: %s\n"
            "*** Fix backend/.env (DB_USER/DB_PASSWORD/DB_NAME), ensure MySQL is running, or run: python init_db.py --demo\n", e)


ensure_tables()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    if os.getenv("FLASK_ENV") == "production":
        from waitress import serve
        serve(app, host="0.0.0.0", port=port)
    else:
        app.run(host="127.0.0.1", port=port, debug=True)
