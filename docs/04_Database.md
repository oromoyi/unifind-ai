# Database documentation

Engine: MySQL 8 (InnoDB, utf8mb4). Schema: `database/schema.sql` (generated from the SQLAlchemy models by `database/generate_sql.py`, and loaded successfully into MariaDB 10.11 during development). Reference data: `database/seed_reference.sql`. Demo data: `backend/seed.py` (calls the real API).

| Table | Purpose | Key constraints / indexes |
|---|---|---|
| `users` | accounts | PK id; UNIQUE email, student_id; FK role_id; failed_logins, locked_until |
| `roles`, `permissions`, `role_permissions` | RBAC | UNIQUE name/code; composite PK on the link table |
| `item_categories`, `campus_locations` | catalogue (+ x/y metres for proximity) | UNIQUE name; `is_active` soft-disable |
| `lost_reports` | lost items | FK user, category, location; indexes on status, category, user, lost_date |
| `found_items` | found items; `private_details`, `verification_*` columns are private | FK reporter, category, location; indexes on status, category, found_date |
| `item_images` | photos (file names only) | FK to found_items or lost_reports, ON DELETE CASCADE |
| `claims` | ownership claims | FK item, claimant, lost_report, reviewer; flags `suspicious`, `auto_check_passed` |
| `claim_verifications` | one row per answer check (question, **salted hash**, matched) | FK claim CASCADE |
| `handovers` | physical return | UNIQUE claim_id, UNIQUE reference_code |
| `feedback` | rating 1–5 per handover | UNIQUE handover_id |
| `notifications` | in-app messages | index (user_id, is_read) |
| `audit_logs` | who did what, when, from which IP, JSON details | indexes on user, action, entity_type, created_at |
| `matching_results` | stored suggestions with JSON breakdown | UNIQUE (lost_report_id, found_item_id) |
| `settings` | admin configuration (JSON values) | PK key |
| `contact_messages` | contact form | |

**Transactions:** claim approval and handover completion lock rows with `SELECT … FOR UPDATE` and commit once; any exception triggers rollback (`test_approval_rolls_back_on_failure`).
**Normalisation:** 3NF for transactional data; JSON columns only for audit details, settings and score breakdowns (read as a unit).
**Privacy:** verification answers are PBKDF2-HMAC-SHA256 (50 000 iterations, per-item 128-bit salt) over a normalised answer; passwords use Werkzeug's salted hashing.
