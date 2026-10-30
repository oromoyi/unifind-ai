# User manual

## Everyone
* **Theme:** moon/sun button (top bar). **Skip link** and keyboard navigation are supported; focus rings are always visible.
* **Browse found items** (no login): search keywords, filter by category/location/colour/date, sort, page. Only public descriptions are shown.

## Student / staff member
1. **Register** (role *Student*, student ID in the university format) and log in.
2. **Report lost item:** title, category, where/when, colour, brand, description, optional photos. If a similar report exists you are asked to confirm.
3. **Suggested matches:** each card shows a score, a plain-language reason and a score breakdown. This is only a hint.
4. **Claim:** open the item → *This is mine* → answer the verification question and describe private details. You do not see whether the answer matched; an officer decides. Max 3 attempts per item (default).
5. **My claims / Notifications:** track status; withdraw pending claims.
6. **Collect:** after approval open *Handovers*, note the code (e.g. `UF-7K3M9QAB`), bring photo ID to the office. After collection download the **PDF receipt** and rate the service.

## Finder
Register as *Finder* → **Register found item**: public description (no secrets), photos, and a **private question + answer** only the owner would know (stored as a salted hash). Hand the item to Security. Your item appears publicly after officer approval. Track status under *My found items*.

## Officer
* **Register received item** (published immediately; add storage location).
* **Items & claims → Claims:** review claimant details, description, private details on file and the automatic answer check; ⚠ flags show suspicious claims. Approve/reject with a reason.
* **Found items / Lost reports tabs:** approve, reject (reason), archive.
* **Handovers:** select *Record handover*, enter the code the claimant shows, tick the ID check, confirm. Wrong codes are logged.
* **Analytics:** KPIs and charts.

## Administrator
All officer functions plus: **Users & roles** (create staff, change roles, deactivate, unlock, edit permission matrix); **Categories & locations** (with x/y metres for proximity); **Matching & rules** (weights, thresholds, claim attempts, student-ID pattern, moderation keywords, *Recompute matches*); **Audit log**; **Analytics & research** (CSV/PDF export, baseline-vs-matcher evaluation).
