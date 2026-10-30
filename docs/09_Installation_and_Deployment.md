# Installation and deployment

See `README.md` for the Windows/VS Code walkthrough. This file covers production-style deployment.

## Environment variables (`backend/.env`)
`SECRET_KEY` (required in production), `JWT_EXPIRES_HOURS`, `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` or `DATABASE_URL`, `CORS_ORIGINS`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `STORAGE_BACKEND=local|s3` (S3 needs `pip install boto3`, `S3_BUCKET`, `S3_REGION`, AWS credentials; photo similarity is skipped for S3-stored images), `SMTP_*` (optional e-mail), `RATELIMIT_ENABLED`, `FLASK_ENV=production`, `PORT`.

## Production on a single server (Windows or Linux)
1. Install MySQL 8, create DB and a least-privilege user (README step 3).
2. `cd backend; python -m venv .venv; pip install -r requirements.txt` and fill `.env` with `FLASK_ENV=production`.
3. `python seed.py --bootstrap-only` (roles, permissions, categories, locations only).
4. Create the first administrator: register normally, then in MySQL:
   `UPDATE users SET role_id=(SELECT id FROM roles WHERE name='admin') WHERE email='you@university.edu';`
5. Run the API: `python run.py` (uses Waitress when `FLASK_ENV=production`) or `gunicorn -w 2 run:app` on Linux.
6. Build the frontend: `cd frontend; npm ci; npm run build`; serve `frontend/dist` with nginx/IIS and proxy `/api/` and `/uploads/` to the API (see `frontend/nginx.conf`). Add HTTPS.
7. Back up MySQL (`mysqldump unifind`) and the `uploads` directory regularly.

## Docker (untested here)
```powershell
copy deploy\.env.compose.example .env     # edit secrets
docker compose up --build                  # http://localhost:8080
```
Set `SEED_ARGS=` (empty) in `.env` to load demo accounts, otherwise only reference data is created.

## Upgrading the schema
The project uses `db.create_all()` (creates missing tables only). For production schema evolution introduce Alembic/Flask-Migrate; this is listed as future work.
