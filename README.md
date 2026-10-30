# UniFind AI — Smart University Lost-and-Found and Property Recovery System

A full-stack graduation-project system: **React + Vite + Tailwind** frontend, **Flask REST API**, **MySQL** database, an **explainable matching engine** (scikit-learn TF-IDF + weighted signals), secure ownership verification, officer handover workflow, analytics, CSV/PDF exports, audit log and a research-evaluation dashboard.

> **Honesty notes** (important for your defence)
> * The matching engine only *suggests* candidates; it never proves ownership or releases an item.
> * "Image similarity" is implemented as a **colour-histogram comparison** (Pillow). It is *not* deep learning. A documented extension point exists for a pretrained CNN (`docs/IMAGE_MATCHING.md`).
> * The bundled evaluation dataset is **synthetic**. The metrics it produces demonstrate the methodology; they are not real-world performance or user-survey results.
> * Demo accounts/data are fictional. Docker files are provided but were not run in the authoring environment.

## What is implemented

| Area | Implemented |
|---|---|
| Roles | Student, Finder, Officer, Administrator (public registration only creates student/finder) with DB-backed, admin-editable permissions |
| Reporting | Lost reports & found items with photos, categories, locations, dates, colour/brand; duplicate detection; moderation keywords |
| Search | Public search over *public* fields with category/location/colour/date filters, sorting, pagination |
| Matching | Category, TF-IDF cosine description similarity, colour/brand, location proximity, date, optional photo colour-histogram; weights/thresholds editable by admin; per-factor explanations |
| Claims | Private verification question (salted PBKDF2 hash), attempt limits, suspicious-claim flags, officer approve/reject with recorded reasons, transactional approval |
| Handover | Unique code, ID-check confirmation, PDF receipt, feedback rating, lifecycle timeline |
| Notifications | In-app (match, claim, approval/rejection, ready for collection, handover) + optional SMTP e-mail |
| Admin | Users, roles/permissions, categories, locations, settings, audit log, KPIs, charts, CSV/PDF export, research evaluation |
| Security | Password hashing, JWT, RBAC, parameterised SQL (ORM), upload validation & re-encoding, rate limiting, account lockout, CORS, security headers, CSV-injection guard |
| Tests | 40 pytest tests (auth, permissions, items, matching, claims, handover, audit, uploads, exports) + 6 Vitest component tests |

## Repository layout

```
backend/      Flask API (app/), tests/, evaluation/ (dataset + generator), seed.py, requirements.txt, .env.example
frontend/     React app (src/), package.json, Tailwind config, Vitest tests
database/     schema.sql, seed_reference.sql, generate_sql.py
docs/         API, academic documentation, diagrams, testing, user manual, deployment, defence Q&A
deploy/       Docker notes; docker-compose.yml + Dockerfiles are at root / in each folder
setup.ps1     One-shot Windows setup script
```

## Quick start on Windows 10/11 (PowerShell + VS Code)

Prerequisites: **Python 3.11+**, **Node.js 20+**, **MySQL 8** (or MariaDB 10.5+), **VS Code**. Check:

```powershell
python --version; node --version; npm --version; mysql --version
```

### 1. Get the code
```powershell
cd $HOME\Documents
Expand-Archive .\unifind-ai.zip -DestinationPath .
cd .\unifind-ai
code .
```

### 2. Install dependencies
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```
(or manually: `cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; cd ..\frontend; npm install`)

### 3. Configure the backend (`backend\.env`)
`setup.ps1` creates `backend\.env` from `.env.example`. Edit it (Notepad / VS Code):
```
SECRET_KEY=<any long random text>      # generate: python -c "import secrets; print(secrets.token_urlsafe(48))"
DB_HOST=127.0.0.1
DB_USER=unifind                        # the app user that will be created for you
DB_PASSWORD=ChooseAStrongPasswordHere  # you choose it; init_db.py creates the user with this password
DB_NAME=unifind
```
(If you prefer to use `root` directly, set `DB_USER=root` and `DB_PASSWORD=<your root password>`.)

### 4. Create the database, tables and demo data — one command
Make sure MySQL is running (`Get-Service *mysql*`; start with `Start-Service MySQL80`). Then:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python init_db.py --demo
```
It asks for your **MySQL root password**, creates the database + app user, creates all tables, loads roles/permissions/categories/locations and the fictional demo accounts. Re-run with `--reset --demo` to wipe and rebuild. Without `--demo` only reference data is loaded.
(Manual alternative: run `database\schema.sql` and `database\seed_reference.sql` with the mysql client, then `python seed.py`.)

### 5. (nothing — tables are also auto-created each time `python run.py` starts)

### 5. Run (two terminals, or VS Code *Terminal → Split*)
```powershell
# Terminal 1 – API on http://127.0.0.1:5000
cd backend; .\.venv\Scripts\Activate.ps1; python run.py

# Terminal 2 – web app on http://localhost:5173
cd frontend; npm run dev
```
Open **http://localhost:5173**.

### Demo accounts (fictional, created by `seed.py`)
| Role | Email | Password |
|---|---|---|
| Administrator | admin@unifind.test | Admin@12345 |
| Officer | officer@unifind.test | Officer@12345 |
| Student | student1@unifind.test (also 2, 3) | Student@12345 |
| Finder | finder1@unifind.test | Finder@12345 |

**Change or delete these accounts before any real deployment.** For production use `python seed.py --bootstrap-only` and create the first administrator by hand (see `docs/09_Installation_and_Deployment.md`).

### 6. Run the tests
```powershell
cd backend; .\.venv\Scripts\Activate.ps1; python -m pytest -v        # uses in-memory SQLite, no MySQL needed
cd ..\frontend; npm test
```
Evaluate matching offline: `cd backend; python -c "import json; from app.evaluation import run_evaluation; from app.settings_store import DEFAULTS; print(json.dumps(run_evaluation(DEFAULTS['match_weights']), indent=1))"`

## Suggested 10-minute demo script
1. Log in as **student2** → *Suggested matches* → expand the score breakdown (explainability).
2. Browse found items anonymously → note that no private details are visible.
3. As **student1** open another item → submit a claim with a wrong answer → see it flagged for staff.
4. As **officer** → *Items & claims* → inspect the flagged claim (auto-check = did not match), reject with a reason.
5. As **officer** approve student3's claim → student3 sees a handover code → officer completes the handover with the code + ID confirmation → download the PDF receipt → student gives feedback.
6. As **admin** → *Analytics & research*: KPIs, charts, CSV/PDF export, keyword-baseline vs matcher evaluation; *Items & claims → Matching & rules* to change weights; *Audit log*.

## Troubleshooting

| Symptom | Fix |
|---|---|
| **`Internal server error` / `Database problem` (HTTP 500/503)** | The API cannot use the database. Read the backend terminal: it prints the real cause. Usual fixes: MySQL not running; wrong `DB_USER/DB_PASSWORD` in `backend\.env`; database not created → run `python init_db.py --demo`. |
| `Access denied for user 'unifind'` | Re-check `DB_USER/DB_PASSWORD` in `backend\.env`; ensure step 3 ran on the same MySQL server. |
| `Can't connect to MySQL server` | Start the *MySQL80* Windows service (`Start-Service MySQL80`) and confirm `DB_HOST=127.0.0.1`, `DB_PORT=3306`. |
| `cryptography`/`PyMySQL` auth errors with MySQL 8 | Keep the `cryptography` package installed (it is in requirements.txt); required for `caching_sha2_password`. |
| PowerShell blocks `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Frontend shows "Cannot reach the server" | Backend not running on port 5000; the Vite dev server proxies `/api` and `/uploads` there. |
| Images don't show | Ensure the backend can write `backend\uploads\`; re-seed if you deleted it. |
| `429 Too many requests` | Rate limiting (login 15/5 min, register 10/h, claims 20/h). Wait, or set `RATELIMIT_ENABLED=false` in `.env` during development. |
| Port 5000 busy | Set `PORT=5001` in `.env` and update `vite.config.js` proxy target. |

## Documentation index
`docs/API.md` · `docs/01_Proposal_and_Academic_Report.md` · `docs/02_Requirements_and_Use_Cases.md` · `docs/03_UML_and_Architecture.md` · `docs/04_Database.md` · `docs/05_Testing_and_Evaluation.md` · `docs/06_User_Manual.md` · `docs/07_Presentation_and_Defense.md` · `docs/08_Security_Review.md` · `docs/09_Installation_and_Deployment.md` · `docs/IMAGE_MATCHING.md`
#   u n i f i n d - a i  
 