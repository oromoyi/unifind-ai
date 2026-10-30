# Final presentation outline and defence Q&A

## Presentation outline (≈20 min + 10 min questions)
1. Title, team, supervisor (1 slide)
2. Problem: how lost property is handled today; consequences (2)
3. Objectives and research questions (1)
4. Related work in one slide: TF-IDF, histogram matching, RBAC, OWASP (1)
5. System overview & roles; architecture diagram (2)
6. Database and lifecycle diagram (1)
7. **Live demo** (6–7 min): follow the script in README
8. Matching engine: signals, formula, explanation; why explainable (2)
9. Security design: verification hashing, attempt limit, RBAC, uploads, audit (2)
10. Testing: 40 backend + 6 frontend tests; checklist (1)
11. Evaluation: methodology, results *with caveats* (2)
12. Limitations and future work (1)
13. Conclusion and lessons learned (1)

## Model answers to likely questions
**Q1. Is this really "AI"?** It is classical machine-learning-based information retrieval: TF-IDF vectors and cosine similarity from scikit-learn, combined with hand-designed signals in a transparent weighted model. There is no neural network. We chose this deliberately for explainability and small-data suitability; a CNN image embedding is the documented extension.

**Q2. How do you prevent someone claiming an item that is not theirs?** The finder sets a private question whose answer is stored only as a salted PBKDF2 hash. Claims are limited to 3 attempts per item, repeated/mismatching claims are flagged, the claimant is not told whether the answer matched (prevents guess-and-check), and a human officer verifies evidence and ID. The item is released only with a one-time handover code *and* an ID check, and everything is audited.

**Q3. Can the system auto-return an item?** No. Matching only suggests; status changes require officer actions (tested: `test_match_never_changes_item_status`).

**Q4. How did you evaluate accuracy? Are the numbers real?** We built a labelled benchmark and compute Precision@1, hit-rate@k, MRR and P/R/F1 by threshold against a keyword baseline. The numbers are real *outputs* but from a **synthetic** dataset, so they illustrate the method and are optimistic; real validation needs a pilot with labelled data. We report no user-survey results because none were collected.

**Q5. Why weighted scoring instead of training a classifier?** There is no labelled historical data at the start (cold-start). A configurable linear score is explainable, tunable by administrators, and can later be replaced by a learned model (e.g. logistic regression on the same signals) once real confirmed matches exist.

**Q6. What if a lost report has no photo or colour?** Missing signals are excluded and weights re-normalised, so absence is not penalised.

**Q7. How is SQL injection prevented?** All queries use the SQLAlchemy ORM with bound parameters; LIKE wildcards are escaped; there's a test with a SQL-injection string.

**Q8. How are passwords stored?** Werkzeug salted hashes (never plain text); policy ≥ 8 chars with letters and digits; lockout after 5 failures.

**Q9. Where are the weaknesses?** Token in browser storage, in-memory rate limiter, colour-histogram photo similarity is crude, no 2FA, synthetic evaluation, no load test, no Amharic/Afan Oromo UI.

**Q10. What happens with two claims for one item?** Approval runs in a transaction with row locks; the first approved claim wins and competing pending claims are automatically rejected with a notification.

**Q11. How does it scale?** Matching is O(lost × found) in memory with TF-IDF fitted per run; fine for thousands of records. For larger scale: incremental indexes, candidate pre-filtering by category/date, Redis rate limiting, background workers.

**Q12. How do you handle privacy?** Public API serialises only public fields; phone/email visible only to staff reviewing claims; audit log records access to sensitive actions; data minimisation; ethics approval needed for pilot.

**Q13. Why Flask/React/MySQL?** Mandated stack; widely taught, free, runs on a university server; SQLAlchemy provides parameterised queries and portability.

**Q14. What is your contribution compared with a simple form + spreadsheet?** Explainable ranking, fraud-resistant verification, auditable lifecycle, analytics, role-based workflow.

**Q15. What would you do next?** Pilot at one faculty, collect labelled outcomes, learn weights, CNN/CLIP embeddings, SMS/Telegram notifications, QR labels for found items, Amharic/Afan Oromo UI, integration with student information system.
