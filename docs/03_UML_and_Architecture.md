# UML, ER and architecture diagrams

All diagrams are Mermaid (render in VS Code with the *Markdown Preview Mermaid Support* extension, on GitHub, or export PNGs with `mmdc`). PNG exports are in `docs/diagrams/`.

## 1. System architecture
```mermaid
flowchart LR
  subgraph Client["Browser (React + Vite + Tailwind)"]
    UI["Pages & components"] --> APIc["fetch API client (JWT)"]
  end
  APIc -->|HTTPS JSON / multipart| Flask
  subgraph Server["Flask REST API"]
    Flask["Blueprints: auth, items, claims, notifications, admin, public"]
    Sec["security.py: JWT, RBAC, rate limit, hashing"]
    Match["matching.py: TF-IDF + weighted signals"]
    Util["utils.py: audit, notify, upload validation"]
    Flask --> Sec
    Flask --> Match
    Flask --> Util
  end
  Flask -->|SQLAlchemy ORM, transactions| DB[("MySQL 8")]
  Util --> FS[["Image storage: local folder / S3 option"]]
  Util -.optional.-> SMTP["SMTP e-mail"]
```

## 2. Use-case diagram
```mermaid
flowchart LR
  S([Student]) --- UC1(Report lost item)
  S --- UC2(Browse / search found items)
  S --- UC3(View suggested matches)
  S --- UC4(Submit ownership claim)
  S --- UC5(Track claims, notifications)
  S --- UC11(Give recovery feedback)
  F([Finder]) --- UC6(Register found item)
  F --- UC7(Track item status)
  O([Officer]) --- UC6
  O --- UC8(Review and verify claims)
  O --- UC9(Record handover and receipt)
  O --- UC12(Moderate reports)
  A([Administrator]) --- UC10(Manage users and permissions)
  A --- UC13(Configure categories, locations, matching)
  A --- UC14(View analytics, audit log, exports)
  A --- UC8
  A --- UC12
```

## 3. Activity diagram – from lost report to return
```mermaid
flowchart TD
  A([Student reports lost item]) --> B{Duplicate of own report?}
  B -- yes --> B1[Warn; user confirms or edits] --> C
  B -- no --> C[Save report, run matching]
  C --> D{Finder/officer registers found item}
  D --> E[Officer approves finder item] --> F[Matching runs against open lost reports]
  F --> G{Score >= notify threshold?}
  G -- yes --> H[In-app notification to owner]
  G -- no --> I[Stored if >= min score, no alert]
  H --> J[Student opens item and submits claim + answer]
  I --> J
  J --> K{Attempt limit reached?}
  K -- yes --> K1[Blocked: visit office] --> Z([End])
  K -- no --> L[Hash answer, compare, flag if suspicious]
  L --> M[Officer reviews evidence]
  M --> N{Verified?}
  N -- no --> O[Reject with reason, notify] --> Z
  N -- yes --> P[Approve in one transaction: item claimed, handover code created]
  P --> Q[Student shows ID + code at office]
  Q --> R{Code correct and ID checked?}
  R -- no --> Q
  R -- yes --> S[Item returned, receipt PDF, feedback] --> Z
```

## 4. Sequence diagram – claim approval and handover
```mermaid
sequenceDiagram
  actor St as Student
  actor Officer
  participant UI as React UI
  participant API as Flask API
  participant DB as MySQL
  St->>UI: Submit claim (description, answer)
  UI->>API: POST /found/{id}/claims
  API->>DB: INSERT claim, claim_verification(hash), audit_log
  API-->>UI: 201 (no match result revealed)
  API->>DB: INSERT notifications (staff, finder)
  Officer->>UI: Approve with reason
  UI->>API: POST /claims/{id}/approve
  API->>DB: BEGIN, SELECT ... FOR UPDATE (claim, item)
  API->>DB: UPDATE claim, item=claimed, reject competing claims
  API->>DB: INSERT handover(code), notifications, audit_log
  API->>DB: COMMIT
  API-->>UI: 200
  St->>Officer: Shows ID and handover code
  Officer->>API: POST /handovers/{id}/complete (code, id_verified)
  API->>DB: BEGIN, verify code, item=returned, lost=recovered, COMMIT
  API-->>Officer: 200 + receipt available
```

## 5. Class diagram (domain model)
```mermaid
classDiagram
  class User { id; full_name; email; password_hash; student_id; is_active; locked_until }
  class Role { id; name }
  class Permission { id; code }
  class LostReport { id; title; description; color; brand; lost_date; status }
  class FoundItem { id; title; public_description; private_details; verification_answer_hash; found_date; status }
  class ItemImage { id; filename }
  class Claim { id; description; status; auto_check_passed; suspicious; review_reason }
  class ClaimVerification { id; question; submitted_answer_hash; matched }
  class Handover { id; reference_code; status; id_verified; completed_at }
  class MatchingResult { id; score; breakdown; explanation }
  class Notification { id; type; message; is_read }
  class AuditLog { id; action; entity_type; entity_id; details; ip_address }
  class Feedback { id; rating; comment }
  User "*" --> "1" Role
  Role "*" -- "*" Permission
  User "1" --> "*" LostReport : reports
  User "1" --> "*" FoundItem : registers
  LostReport "1" --> "*" ItemImage
  FoundItem "1" --> "*" ItemImage
  FoundItem "1" --> "*" Claim
  User "1" --> "*" Claim : claimant
  Claim "1" --> "*" ClaimVerification
  Claim "1" --> "0..1" Handover
  Handover "1" --> "0..1" Feedback
  LostReport "1" --> "*" MatchingResult
  FoundItem "1" --> "*" MatchingResult
  User "1" --> "*" Notification
  User "1" --> "*" AuditLog
```

## 6. Entity-relationship diagram
```mermaid
erDiagram
  roles ||--o{ users : has
  roles }o--o{ permissions : role_permissions
  users ||--o{ lost_reports : files
  users ||--o{ found_items : registers
  users ||--o{ claims : submits
  users ||--o{ notifications : receives
  users ||--o{ audit_logs : performs
  item_categories ||--o{ lost_reports : classifies
  item_categories ||--o{ found_items : classifies
  campus_locations ||--o{ lost_reports : where
  campus_locations ||--o{ found_items : where
  found_items ||--o{ claims : claimed_by
  claims ||--o{ claim_verifications : checks
  claims ||--o| handovers : results_in
  handovers ||--o| feedback : rated_by
  lost_reports ||--o{ matching_results : scored
  found_items ||--o{ matching_results : scored
  found_items ||--o{ item_images : photos
  lost_reports ||--o{ item_images : photos
```
