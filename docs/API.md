# REST API reference

Base URL `http://127.0.0.1:5000/api`. JSON unless noted. Authenticated calls send `Authorization: Bearer <token>` (JWT, HS256, default 8 h). Errors: `{"error": "...", "fields": {"field": "message"}}`. Common statuses: 401 not authenticated, 403 not permitted, 404 not found *or not yours*, 409 state conflict / duplicate, 422 validation, 423 account locked, 429 rate-limited.

Permissions (editable by admin): `lost.create`, `found.create`, `claims.create`, `items.review`, `claims.review`, `handovers.manage`, `users.manage`, `roles.manage`, `settings.manage`, `audit.view`, `analytics.view`, `reports.export`.

## Auth
| Method & path | Access | Notes |
|---|---|---|
| POST `/auth/register` | public, 10/h | body `full_name,email,password,role(student|finder),student_id?,department?,phone?` → `{token,user}`. Privileged roles are rejected. |
| POST `/auth/login` | public, 15/5 min | `{email,password}`; 5 failures lock the account 15 min (423). |
| GET `/auth/me` · PUT `/auth/me` | any user | profile (`full_name,department,phone`) |
| POST `/auth/change-password` | any user | `{current_password,new_password}` |

## Public
| GET `/meta` | categories, locations, university name, departments |
|---|---|
| GET `/stats/public` | live counts and recovery rate |
| POST `/contact` | `{name,email,message}` (5/h) |

## Lost reports (students)
| Method & path | Access | Notes |
|---|---|---|
| POST `/lost` | `lost.create` | multipart/form-data: `title,category_id,description,location_id,date,color?,brand?,distinguishing_features?,images[]` (≤4). 409 `{duplicate:true,duplicates:[…]}` unless `confirm_duplicate=1`. Returns report + top matches. |
| GET `/lost?status&q&category_id&scope=all&page` | owner; staff with `items.review` + `scope=all` | |
| GET/PUT `/lost/<id>` | owner/staff (others get 404) | |
| POST `/lost/<id>/close` | owner | |
| GET `/lost/<id>/matches?refresh=1` | owner/staff | ranked matches with `score`, `explanation`, `breakdown` |
| GET `/matches` | student | all matches across own open reports |
| POST `/lost/<id>/review` | `items.review` | `{decision: approve|reject|archive, reason}` |

## Found items
| POST `/found` | `found.create` | multipart as above plus `verification_question`, `verification_answer` (hashed), `private_details`, `storage_location`. Finder items start `pending`; officer/admin items are `available`. |
|---|---|---|
| GET `/found?q&category_id&location_id&color&date_from&date_to&sort=newest|oldest|title&page&per_page` | public (only `available`, public fields) | `mine=1` for the reporter; `scope=all&status=` for reviewers |
| GET `/found/<id>` | public if available; reporter/staff/claimant otherwise | private fields only for reporter/staff |
| PUT `/found/<id>` | reporter/staff | |
| POST `/found/<id>/review` | `items.review` | approve / reject(reason) / archive |
| GET `/found/<id>/timeline` | as item visibility | lifecycle events (no identities) |

## Claims & handovers
| POST `/found/<id>/claims` | `claims.create`, 20/h | `{description, verification_answer, lost_report_id?}`. Result never reveals whether the answer matched. Max attempts per item = setting (default 3). |
|---|---|---|
| GET `/claims?status&suspicious=1&page` | own claims; staff (`claims.review`) see all with private evidence | |
| GET `/claims/<id>` · POST `/claims/<id>/withdraw` | claimant/staff | |
| POST `/claims/<id>/approve` · `/reject` | `claims.review` | `{reason}` (≥5 chars). Approval is one DB transaction (row locks): claim→approved, item→claimed, competing claims rejected, handover code created, notifications, audit. |
| GET `/handovers?status` | claimant (sees `reference_code`) / staff (`handovers.manage`, code hidden) | |
| POST `/handovers/<id>/complete` | `handovers.manage` | `{reference_code,id_verified:true,notes?}` transaction: item→returned, lost report→recovered |
| GET `/handovers/<id>/receipt` | claimant/staff | PDF, after completion |
| POST `/handovers/<id>/feedback` | claimant | `{rating 1-5, comment?}` once |

## Notifications
GET `/notifications?unread=1&page` · GET `/notifications/unread-count` · POST `/notifications/<id>/read` · POST `/notifications/read-all`

## Administration (`/admin/...`)
| GET/POST `/users`, PUT `/users/<id>` | `users.manage` | create staff, change role, activate/deactivate, unlock. Cannot demote/deactivate self. |
|---|---|---|
| GET `/roles`, PUT `/roles/<id>/permissions` | `roles.manage` | admin role is immutable |
| GET/POST/PUT `/categories`, `/locations` | `settings.manage` | soft-disable via `is_active`; locations carry x/y metres |
| GET/PUT `/settings` | `settings.manage` | `match_weights, match_min_score, match_notify_score, match_max_results, max_claim_attempts, student_id_pattern, blocked_keywords, departments, university_name` |
| POST `/rematch` | `settings.manage` | recompute matches for open reports |
| GET `/audit?action=prefix&entity_type` | `audit.view` | |
| GET `/analytics` | `analytics.view` | KPIs, monthly series, per-category, statuses |
| GET `/evaluation` | `analytics.view` | baseline vs matcher metrics on the labelled dataset |
| GET `/export/<summary|found-items|lost-reports|claims>?format=csv|pdf` | `reports.export` | CSV cells starting with `= + - @` are prefixed with `'` |
| GET `/contact-messages` | `users.manage` | |
