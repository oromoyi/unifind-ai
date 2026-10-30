# System requirements specification

## 1. Functional requirements
| ID | Requirement | Status |
|---|---|---|
| FR-01 | Students and finders can self-register; officer/admin accounts only via administrator | Implemented |
| FR-02 | Secure login/logout, profile edit, password change | Implemented |
| FR-03 | Student reports lost item (photos, category, date, location, colour, brand, features) | Implemented |
| FR-04 | Finder/officer registers found item with public description and private verification data | Implemented |
| FR-05 | Public search/filter/sort/paginate of available found items (public fields only) | Implemented |
| FR-06 | Matching engine ranks found items per lost report with explanation and score 0–100 | Implemented |
| FR-07 | Admin configures weights, thresholds, attempt limits, moderation keywords | Implemented |
| FR-08 | Duplicate-report detection | Implemented |
| FR-09 | Claim submission with private answer; attempt limiting; suspicious flags | Implemented |
| FR-10 | Officer approves/rejects claims with recorded reason (transactional) | Implemented |
| FR-11 | Unique handover code; officer completes handover with ID confirmation; PDF receipt | Implemented |
| FR-12 | In-app notifications for match, claim, decision, ready, handover; optional e-mail | Implemented (e-mail untested on live SMTP) |
| FR-13 | Admin manages users, roles, permissions, categories, locations | Implemented |
| FR-14 | Audit log of important actions | Implemented |
| FR-15 | Analytics: recovery rate, time-to-recovery, trends, feedback | Implemented |
| FR-16 | CSV/PDF export | Implemented |
| FR-17 | Post-recovery feedback | Implemented |
| FR-18 | Research dashboard: baseline vs matcher | Implemented |
| FR-19 | Deep-learning image matching | Future work |
| FR-20 | SMS / mobile app / multilingual UI | Future work |

## 2. Non-functional requirements
| ID | Requirement | How addressed |
|---|---|---|
| NFR-01 Security | Hashed passwords, RBAC, SQL-injection protection, safe uploads, rate limiting | See `08_Security_Review.md` |
| NFR-02 Privacy | Private details never in public responses | Tested (`test_items.py`) |
| NFR-03 Usability | Responsive, accessible (labels, focus, ARIA live, keyboard), light/dark themes | Implemented; no formal usability study |
| NFR-04 Performance | Lists paginated; matching O(L×F) in memory | Suited to thousands of items; no load test performed |
| NFR-05 Reliability | Transactions for approval/return, rollback test | Tested |
| NFR-06 Maintainability | Modular blueprints, settings in DB, tests | Implemented |
| NFR-07 Portability | Windows/Linux, MySQL 8/MariaDB, Docker option | Local run verified on MariaDB 10.11; Docker untested |

## 3. Use-case descriptions (key cases)
**UC-01 Report lost item** — *Actor:* Student. *Pre:* logged in. *Main flow:* fill form → system validates → duplicate check → saves → runs matching → shows top matches. *Alternate:* duplicate found → user confirms or edits; invalid image → error. *Post:* report `open` (or `pending` if moderation keyword hit); audit entry.

**UC-02 Register found item** — *Actor:* Finder/Officer. *Main:* enter public description, optional private question/answer/details → saved (`pending` for finders, `available` for officers) → reviewers notified → on approval matching runs against open lost reports and owners are notified at ≥ notify score.

**UC-03 Claim item** — *Actor:* Student. *Pre:* item available, user not reporter, attempts < limit, no pending claim. *Main:* describe item, answer question → answer normalised and hashed with the item's salt → compared in constant time → claim `pending`, flagged if mismatch/repeat/many claims → staff notified. The claimant is *not* told whether the answer matched.

**UC-04 Review claim** — *Actor:* Officer/Admin. *Main:* inspect claimant details, description, private details, auto-check → approve (reason required) or reject (reason required). *Approve post:* item `claimed`, competing claims rejected, handover created, notifications sent — all in one transaction.

**UC-05 Complete handover** — *Actor:* Officer. *Main:* claimant presents ID and code → officer enters code and confirms ID check → item `returned`, lost report `recovered`, receipt available. *Alternate:* wrong code → rejected and audited.

**UC-06 Administer system** — *Actor:* Admin. Users/roles/permissions, categories/locations, matching settings, audit, analytics, exports.

## 4. Item lifecycle
Found item: `pending → available → claimed → returned → archived` (or `rejected`). Lost report: `pending/open → matched → recovered` (or `closed`, `rejected`, `archived`). Every transition is audit-logged; `GET /found/<id>/timeline` exposes identity-free events.
