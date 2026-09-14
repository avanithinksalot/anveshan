MASTER PROMPT — MPLADS AI Anomaly Detection Platform (SIH26102 Prototype Build)

ROLE
You are building a working hackathon prototype of an AI-powered fraud/anomaly
detection platform for MPLADS (Members of Parliament Local Area Development
Scheme), based on the technical solution document below. Build incrementally,
phase by phase, and confirm with me before moving to the next phase.

====================================================================
CRITICAL — UI/UX DIRECTION (read this before writing any frontend code)
====================================================================
Do NOT build the generic "AI-generated dashboard" look. You know the one:
purple-to-blue gradient hero header, a row of identical rounded white cards
with a big number + tiny label + a stock lucide-react icon in a colored
circle, Inter font, soft drop shadows on everything, generic "Dashboard"
sidebar with a bulleted icon list, and a chart dropped in with default
styling and no real data density. If what you're building could pass for
any SaaS landing page demo, stop and redesign it.

Instead, design this like a real government audit/investigator tool:
- Dense, information-first layouts — auditors want to scan many rows of
  works/risk scores quickly, not admire whitespace. Think Bloomberg
  terminal / internal ops-tool density, not marketing-site spaciousness.
- A real data table as the primary interface for the case queue — sortable,
  filterable columns (Work ID, MP, District, Category, Risk Score, Tier,
  Status) — not cards for list data.
- Risk tiers shown with a deliberate, restrained color system (e.g. a
  muted slate/navy base palette with red/amber/green reserved ONLY for
  risk tiers, so risk color-coding actually stands out instead of
  competing with decorative color everywhere else).
- Typography: pick one serious, slightly technical typeface pairing (e.g.
  IBM Plex Sans + IBM Plex Mono for numbers/IDs/scores) — not the default
  Inter-everywhere look.
- No decorative gradients, no floating blob shapes, no glassmorphism, no
  emoji as icons. If you use icons, use them sparingly and functionally
  (a single consistent icon set, small, monochrome, next to real actions).
- The SHAP explanation panel is a key differentiator in the pitch — design
  it as a real "case file" reading experience (reason codes + weights
  laid out like an audit report), not a chat-bubble or tooltip.
- Reference aesthetic: think of tools built for people who use them 8
  hours a day under fluorescent lights — IRS case-management systems,
  Bloomberg/Palantir-style ops dashboards, banking fraud-ops consoles —
  not consumer app onboarding screens.
- Before writing dashboard components, actually sketch the information
  hierarchy in words first: what does a District Authority need to see
  in the first 3 seconds vs. what they click into. Design from that, not
  from a component library's default template.

If you're using a component library (shadcn/ui, etc.), that's fine — but
override its defaults deliberately (spacing, radius, palette) so it
doesn't read as "default shadcn template." Show me a static mockup of the
main case-queue screen before wiring up any real logic, so we can fix the
visual direction before investing in interactivity.

====================================================================
SYSTEM OVERVIEW (from the technical solution document)
====================================================================
This platform combines four detection mechanisms into one composite Risk
Score (0-100) per MPLADS "work" (a sanctioned project):

1. Hard Rule Engine (deterministic) — explicit MPLADS rule violations:
   1-year completion window, disallowed work categories, allocation
   ceilings, SC/ST quota compliance. ANY hard violation fixes the Risk
   Score at 80-100 regardless of ML output — this must bypass the ML
   pipeline entirely in code, not just in the score formula.

2. Isolation Forest (unsupervised) — anomaly scoring on cost, timeline,
   and vendor-concentration features. No labeled fraud data needed.

3. XGBoost + SMOTE (supervised) — trained on rule-flag patterns + top
   anomalies + real cited CAG audit cases as ground truth. SMOTE balances
   classes since true positives are rare. Outputs a calibrated 0-1 risk
   probability.

4. Similarity Detection —
   - Text: TF-IDF + cosine similarity (rapidfuzz for fast fuzzy matching)
     on Work Description, to catch duplicate/near-duplicate works.
   - Image: perceptual hashing (imagehash library) to catch reused
     completion photos across different "completed" works.

Composite Risk Score formula (implement exactly this):
   IF hard_rule_violation: score = 80-100 (bypass ML)
   ELSE: score = 0.40 * isolation_forest_normalized
               + 0.40 * xgboost_risk_probability
               + 0.20 * avg(vendor_concentration_score, similarity_score)
Risk tiers: Low (0-39), Medium (40-69), High (70-100).

Every flagged work must carry a SHAP-derived plain-language reason string,
e.g. "Flagged due to 340% cost deviation from category median and vendor
active across 6 districts."

====================================================================
DATA ASSETS (real data, from eSAKSHI/MPLADS export — six linked tables)
====================================================================
- Allocated_Limit_for_Honble_MPs (544 rows) — 1 row/MP: State, MP,
  Constituency, Allocated Amount
- Amount_consented_for_Calamity (13 rows) — 1 row/consent event
- Works_Recommended (8,001 rows) — Work (embeds Work ID), Category, MP,
  IDA, Recommended Date/Amount, Sanction Date
- Works_Sanctioned (9,001 rows) — Work, Sanction Date/Amount, Work Status
  (pipeline stage)
- Works_Completed (35,200 rows) — Work, Description, Image, Completion
  Date, Amount Disbursed
- Expenditure_on_Completed_and_On-going_Works (85,120 rows) — Work ID,
  IDA, Vendor Name, Expenditure Date, Payment Status, Fund Disbursed

Join key: every work has an ID embedded as a prefix in the "Work" field
(format like WS/MP<id>/<year>-<year>/<serial>) — extract via regex into a
clean work_id column. This is how all six tables join into one master
lifecycle table: Recommended Amount -> Sanction Amount -> Σ Expenditure ->
Completion Date -> Work Status.

Known real data-quality issues to handle in the ingestion/cleaning layer:
- Stray "Grand Total" footer rows embedded inside data (found in
  Works_Sanctioned)
- Indian comma-formatted numbers (e.g. "17,35,60,04,099.87") need
  normalization before casting to numeric
- "Image" field often literal "N/A" or generic placeholder "Images" —
  treat as missing until a real image URL is confirmed
- Work Description sometimes has garbled/mis-encoded regional-language
  (Hindi) text — needs a language-aware cleaning step, don't just drop
  silently without logging

====================================================================
TECH STACK (use exactly this — it's what the solution document specifies)
====================================================================
- Data processing: Python, pandas, numpy
- ML: scikit-learn (IsolationForest), XGBoost, imbalanced-learn (SMOTE)
- Explainability: SHAP
- Text similarity: scikit-learn (TF-IDF), rapidfuzz
- Image similarity: imagehash, Pillow
- Backend: FastAPI, Uvicorn, Pydantic
- Database: PostgreSQL, SQLAlchemy
- Frontend: React, Tailwind CSS, Recharts or D3.js (for vendor-network
  graphs specifically — D3 for the network graph, Recharts is fine for
  simple trend charts)
- Auth: JWT, role-based access control (MP / District / State / Ministry)
- Deployment: Docker, docker-compose

====================================================================
FEATURES TO ENGINEER (three granularities — build all three)
====================================================================
Work-level: disbursed_vs_sanctioned_ratio, sanction_vs_recommended_diff_pct,
amount_zscore_in_category, days_sanctioned_to_completion, is_overdue_1yr_rule,
work_status_stage_duration, duplicate_work_id_flag, desc_similarity_max_score,
image_duplicate_flag, image_missing_flag, disallowed_category_keyword_flag

Vendor-level: vendor_ida_count, vendor_mp_count, vendor_is_individual_flag,
vendor_concentration_score

MP/scheme-level: allocation_utilization_ratio, calamity_vs_allocation_check,
sc_st_allocation_compliance_ratio, expenditure_spike_before_deadline

====================================================================
API ENDPOINTS (build exactly these)
====================================================================
POST   /ingest                        — load/refresh a batch of source table exports
GET    /works/{work_id}/risk          — risk score, tier, SHAP explanation for a work
GET    /alerts?tier=high&state=...    — list flagged works, filterable by tier/state/IDA/MP
POST   /cases/{work_id}/action        — auditor records cleared/escalated/confirmed
GET    /dashboard/summary?role=...    — aggregated view scoped to caller's role

====================================================================
ROLE-BASED DASHBOARDS (four distinct views, one shared risk engine)
====================================================================
- Ministry (MoSPI): national heat-map of risk by state/IDA, top flagged
  vendors, scheme-wide trend charts, compliance summary
- State Nodal Authority: state-level drill-down, districts ranked by risk,
  cross-district vendor patterns
- District Authority (IDA): case queue for that district, SHAP explanation
  per flagged work, clear/escalate actions — THIS is the primary screen,
  build it first and build it well
- Member of Parliament: personal transparency view — allocation
  utilization, portfolio compliance status — explicitly framed as
  self-verification, not accusation. Tone and design should feel
  supportive/informational for this role, distinct from the
  investigator tone of the District Authority view.

====================================================================
BUILD PHASES — confirm with me after each before continuing
====================================================================
Phase 1: Data ingestion + cleaning pipeline (handle the known data-quality
         issues above), producing the joined master lifecycle table.
Phase 2: Feature engineering (all three granularities).
Phase 3: Rule engine (deterministic checks) — get this fully working and
         tested before touching any ML, since it's the trust foundation.
Phase 4: Isolation Forest + XGBoost + SMOTE + SHAP pipeline, composite
         score calculation exactly as specified above.
Phase 5: Text similarity + perceptual image hashing modules.
Phase 6: FastAPI backend with the five endpoints above, PostgreSQL schema.
Phase 7: Frontend — static mockup of the District Authority case-queue
         screen FIRST (per the UI direction above) for my sign-off, then
         build it out, then the other three role views.
Phase 8: Auditor feedback loop wiring (cleared/escalated actions feed back
         as labels for retraining).

Do not skip ahead to frontend polish before the rule engine and scoring
pipeline are correct — the visual design matters, but a wrong risk score
matters more, and I'd rather see ugly-but-correct before pretty-but-wrong.

Ask me before starting if anything about the data schema or scoring
formula is ambiguous — don't guess and build on a wrong assumption.