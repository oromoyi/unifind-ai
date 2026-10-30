# Deployment configuration

* `../docker-compose.yml` – MySQL 8 + Flask (gunicorn) + React (nginx). Copy `deploy/.env.compose.example` to `.env` in the repository root, set strong values, then `docker compose up --build`. Open http://localhost:8080.
* `../backend/Dockerfile`, `../frontend/Dockerfile`, `../frontend/nginx.conf` – image definitions.
* Production checklist: see `docs/09_Installation_and_Deployment.md`.

The Docker files were written to the same configuration as the local setup but **were not executed in the authoring environment** (no Docker daemon available); test them before relying on them.
