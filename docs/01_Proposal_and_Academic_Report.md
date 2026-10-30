# UniFind AI — Project proposal and academic report

*Status key used throughout: **[Implemented]** = present and tested in this repository; **[Future work]** = proposed only.*

## 1. Abstract
Universities lose and recover a large amount of student property (phones, ID cards, keys, laptops) through informal channels such as notice boards and messaging groups, which are unsearchable, unverifiable and unaccountable. This project designs and implements **UniFind AI**, a web-based lost-and-found system for university campuses. It combines (i) structured lost/found reporting with photographs, (ii) an *explainable* matching engine that ranks candidate pairs using category, TF-IDF text similarity, colour/brand, location proximity, date proximity and a simple photo colour-histogram, (iii) a fraud-resistant claim process using private verification questions stored as salted hashes, attempt limits and officer review, and (iv) auditable handover with unique codes and receipts. The system is built with React, Flask and MySQL, is secured with role-based access control, and includes 40 automated backend tests. Matching quality is evaluated against a keyword-search baseline on a labelled benchmark; the bundled benchmark is synthetic, so reported figures demonstrate the evaluation methodology rather than field performance. A real-world pilot is proposed as future work.

## 2. Introduction and background
Lost property is a routine problem on campuses with thousands of mobile, time-pressured users. Typical practice in many universities, including those in Ethiopia, relies on a security office shelf, paper logs and social-media posts. Weaknesses: no common searchable record, no systematic comparison between what was lost and what was found, no proof that the person collecting an item is its owner, and no statistics to evaluate the service. Information-retrieval techniques (TF-IDF, cosine similarity) and role-based web systems are mature, low-cost technologies suited to a student-built solution that can run on a single university server.

## 3. Problem statement
There is no centralised, searchable, verifiable process for reporting, matching, claiming and returning lost property at the university. Consequences: low recovery rates, slow recovery, risk of fraudulent collection, and no data for management decisions.

## 4. Objectives
**General objective:** design, implement and evaluate a secure web-based system that improves the recovery of lost property at a university.

**Specific objectives**
1. Elicit requirements from the four stakeholder roles (student, finder, officer, administrator).
2. Design a normalised relational database with auditable item lifecycle. **[Implemented]**
3. Implement lost/found reporting, search and photo upload. **[Implemented]**
4. Implement an explainable matching engine with administrator-configurable weights and thresholds. **[Implemented]**
5. Implement secure ownership verification and a controlled handover. **[Implemented]**
6. Provide analytics, exports and an offline evaluation comparing the matcher with keyword search. **[Implemented]**
7. Test functionality and security with automated tests. **[Implemented]**
8. Evaluate with real users and real data at a university. **[Future work]**

## 5. Research questions
* **RQ1.** Does a weighted multi-signal matcher rank the true counterpart item higher than plain keyword search on a labelled benchmark?
* **RQ2.** Which signals contribute most to correct ranking (ablation by changing weights)?
* **RQ3.** Can private verification questions plus attempt limits and staff review reduce the risk of fraudulent claims without blocking genuine owners? (Mechanism implemented; empirical answer requires a pilot — **[Future work]**.)
* **RQ4.** What recovery rate and time-to-recovery does the system record in use? (Instrumented; needs deployment data — **[Future work]**.)

## 6. Scope and limitations
**In scope:** web application for one university (multi-university configuration through settings), the four roles, in-app notifications, optional SMTP e-mail, local image storage.
**Limitations (be explicit in the defence):**
* Matching uses text and metadata; photo similarity is a colour histogram only — it cannot recognise object identity. **[Future work: CNN embeddings]**
* The evaluation dataset is synthetic and cleaner than real reports; the baseline has no access to location/date metadata, so the comparison favours the matcher by design. Real labelled data is needed.
* The in-memory rate limiter is per-process; multi-server deployments need Redis. JWTs are kept in browser storage (XSS exposure) and cannot be revoked before expiry except by deactivating the user.
* No mobile app, SMS, multilingual (Amharic/Afan Oromo) interface, or integration with the university's student information system. **[Future work]**
* E-mail is implemented but untested against a live SMTP server in the authoring environment.

## 7. Literature review (verify every reference before submission)
**Information retrieval and similarity.** Term weighting by TF-IDF, in which a term's weight grows with its frequency in a document and shrinks with its frequency across the collection, is a standard approach to text retrieval (Salton & Buckley, 1988; Manning, Raghavan & Schütze, 2008). Cosine similarity between TF-IDF vectors is a common measure of document similarity and is implemented in scikit-learn (Pedregosa et al., 2011). Retrieval quality is commonly reported with precision, recall, hit-rate at k and Mean Reciprocal Rank (Manning et al., 2008), which this project uses.

**Image similarity.** Colour histograms and histogram intersection for matching images were introduced by Swain & Ballard (1991). They are cheap but ignore shape and texture; modern systems use learned embeddings, which is the proposed extension.

**Explainability.** Users are more likely to act on a recommendation when they understand why it was produced; model-agnostic explanation work (Ribeiro, Singh & Guestrin, 2016) motivates reporting per-factor contributions. UniFind uses a transparent linear score, so explanations are exact rather than approximated.

**Security.** Role-based access control is formalised by Sandhu et al. (1996). Password-storage and authentication guidance is given in NIST SP 800-63B (Grassi et al., 2017). Web risks such as injection, broken access control and insecure file upload are catalogued in the OWASP Top 10 (OWASP Foundation, 2021) and the OWASP Application Security Verification Standard. JSON Web Tokens are specified in RFC 7519 (Jones, Bradley & Sakimura, 2015).

**Gap and local context.** *Students should add 3–5 peer-reviewed or institutional sources on campus lost-and-found systems and on Ethiopian university IT context, found via Google Scholar/Scopus (suggested queries: "lost and found management system web application", "campus lost property matching", "property recovery information system university"). No local sources are cited here because none could be verified in the authoring environment, and invented references would be unacceptable.*

### References
* Grassi, P. A., Garcia, M. E., & Fenton, J. L. (2017). *NIST Special Publication 800-63B: Digital Identity Guidelines — Authentication and Lifecycle Management.* National Institute of Standards and Technology.
* Jones, M., Bradley, J., & Sakimura, N. (2015). *JSON Web Token (JWT).* RFC 7519, IETF.
* Manning, C. D., Raghavan, P., & Schütze, H. (2008). *Introduction to Information Retrieval.* Cambridge University Press.
* OWASP Foundation (2021). *OWASP Top 10:2021.* https://owasp.org/Top10/
* Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830.
* Ribeiro, M. T., Singh, S., & Guestrin, C. (2016). "Why should I trust you?": Explaining the predictions of any classifier. *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, 1135–1144.
* Salton, G., & Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. *Information Processing & Management, 24*(5), 513–523.
* Sandhu, R. S., Coyne, E. J., Feinstein, H. L., & Youman, C. E. (1996). Role-based access control models. *IEEE Computer, 29*(2), 38–47.
* Swain, M. J., & Ballard, D. H. (1991). Color indexing. *International Journal of Computer Vision, 7*(1), 11–32.

## 8. Implementation methodology
Iterative, staged development: (1) requirements, architecture, schema; (2) reusable UI components; (3) API, authentication and RBAC; (4) reporting, search, uploads; (5) matching and explanations; (6) claims, verification, notifications, handover; (7) administration, analytics, exports, audit; (8) automated testing, security review, documentation, deployment. Technology: React 18 + Vite + Tailwind + Recharts; Flask 3 + SQLAlchemy; MySQL 8 (SQLite only for unit tests); scikit-learn; Pillow; ReportLab; PyJWT.

### Matching algorithm
For lost report *l* and found item *f*, each signal *sᵢ ∈ [0,1]*:
* category: 1 if equal else 0
* description: cosine(TF-IDF(l), TF-IDF(f)), unigrams+bigrams, English stop-words removed, sublinear TF, vocabulary fitted on all current texts
* attributes: mean of colour agreement (synonym families, e.g. navy ↔ dark blue = 0.85) and brand agreement; unknown values are skipped
* location: 1 same place; else 0.85·exp(−d/300 m) using campus coordinates
* date: 0 if found >1 day before lost; else exp(−Δdays/14)
* image (optional): colour-histogram intersection, maximum over photo pairs

`score = 100 · Σ wᵢsᵢ / Σ wᵢ` over *available* signals (weights set by the administrator; defaults 0.20/0.30/0.15/0.15/0.10/0.10). The breakdown (value, weight, points) and a sentence such as "Same category, similar description, matching colour/brand, same location, and found shortly after it was lost." are stored with every result. Matches below the minimum score are not stored; matches ≥ the notify score trigger one notification. **A match never changes item status.**

### Evaluation methodology
1. Labelled benchmark: lost reports each paired with exactly one true found item among distractors and hard negatives (`backend/evaluation/`).
2. Baseline: keyword overlap ranking. System under test: weighted matcher with current weights.
3. Metrics: Precision@1, Hit-rate@3/@5, MRR (ranking); precision/recall/F1 over all pairs at thresholds 30–70.
4. Report results with their limitations; repeat on real, anonymised, hand-labelled pairs collected in a pilot, with confidence intervals (e.g. bootstrap over lost reports).
5. Operational metrics from live data: recovery rate, time-to-recovery, feedback ratings, claim rejection and flag rates (dashboard).
6. Suggested user study (**[Future work]**): task-based usability test with ≥15 participants, System Usability Scale questionnaire, and reporting of real survey results only.

Actual measured outputs are in `05_Testing_and_Evaluation.md`.

## 9. Project proposal (summary)
**Title:** UniFind AI — Smart University Lost-and-Found and Property Recovery System. **Duration:** 8 stages (suggested 16 weeks). **Deliverables:** source code, database, tests, documentation, demo. **Resources:** one developer laptop, MySQL, free open-source libraries; one university server for pilot. **Risks:** low adoption (mitigate with officer training and QR posters), fraud attempts (verification + audit), privacy (data minimisation, access control), evaluation data scarcity (synthetic benchmark first, pilot later). **Ethics:** collect only data needed; store contact details privately; obtain university approval and informed consent before any user study; anonymise data used in evaluation.
