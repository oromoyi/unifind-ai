# Security review (self-assessment)

| Control | Implementation | Evidence |
|---|---|---|
| Password hashing | Werkzeug salted hash; policy 8+ chars, letters+digits | `security.py`, `test_auth.py` |
| Authentication | HS256 JWT, expiry (default 8 h), user re-loaded per request so deactivation takes effect immediately | `test_deactivated_user_token_rejected` |
| Brute-force defence | login rate limit 15/5 min per IP, lockout 15 min after 5 failures | `test_wrong_password_and_lockout`, `test_login_rate_limit` |
| Authorisation | permission decorators from DB-backed role matrix; object-level checks return 404 for others' records | `test_permissions.py` |
| No self-escalation | public registration limited to student/finder; admin cannot demote/deactivate self | tests |
| SQL injection | ORM bound parameters; LIKE wildcard escaping | `test_public_search_filters_and_no_private_data` |
| Private data exposure | public serialisers omit private fields; claimant never sees flags, hashes or the match result; staff handover list hides the code | `test_items.py`, `test_claims.py` |
| Verification secrets | PBKDF2-HMAC-SHA256 50k iterations, per-item salt, constant-time compare; submitted answers also stored hashed | `test_claim_correct_answer_not_flagged_and_hash_only` |
| Claim fraud | attempt limit, flags (mismatch, repeat after rejection, ≥3 claims/24 h), mandatory reasons | tests |
| Upload safety | extension allow-list, size limit, Pillow decode + format check, re-encoding (strips EXIF/GPS and appended payloads), random file names | `test_invalid_uploads_rejected` |
| CSRF | Bearer-token API (no cookies) so classic CSRF does not apply | design |
| CORS & headers | origin allow-list from env; `nosniff`, `X-Frame-Options: DENY`, referrer policy | `app/__init__.py` |
| Secrets | from environment / `.env` (git-ignored); production refuses to start without `SECRET_KEY` | `config.py` |
| Export safety | CSV formula-injection guard | `test_exports_csv_pdf_and_injection_guard` |
| Auditability | audit rows for logins, creations, reviews, claims, handovers, exports, settings, role changes | `test_audit_log_entries_for_workflow` |
| Transactions | row-locked approval and return; rollback verified | `test_approval_rolls_back_on_failure` |

## Known gaps / recommendations before real deployment
1. Serve only over HTTPS (reverse proxy) and set `CORS_ORIGINS` to the real origin.
2. JWT in `localStorage` is readable by injected scripts; React escapes output, but consider httpOnly cookies + CSRF tokens for production.
3. In-memory rate limiting is per process and keyed on `remote_addr` (behind a proxy configure `X-Forwarded-For` handling or use Redis/Flask-Limiter).
4. No e-mail verification, password reset, or 2FA for staff — add before launch.
5. Replace demo accounts; rotate `SECRET_KEY`; restrict MySQL user rights; back up the database and uploads.
6. Add a Content-Security-Policy at the reverse proxy.
7. A professional penetration test has **not** been performed.
8. Data-protection: define retention periods and a process for deleting user data on request.
