====================================================================
BUILD PROCESS — MODULE BY MODULE, WITH A TEST + APPROVAL GATE EACH TIME
====================================================================
Build ONE module at a time, in the order below. For every module:

1. Build only that module — do not write code for later modules "while
   you're in there," even if it seems convenient.
2. Write and run a test for that module BEFORE reporting it done:
   - For data/feature/ML modules: run it against a real sample of the
     data and show me actual output (sample rows, a confusion matrix,
     feature values, a risk score breakdown) — not just "it ran without
     errors."
   - For API endpoints: show a real request/response example (curl or
     equivalent) for each endpoint added in that module.
   - For frontend screens: render it and describe/show what's on screen,
     including edge cases (empty state, a High-risk row, a Low-risk row).
3. Give me a short summary: what you built, what you tested, what the
   test showed, and anything that seems off or worth a second look.
4. STOP. Do not start the next module. Wait for me to explicitly say
   "go ahead," "approved," "next module," or similar.
5. Only after I approve do you move to the next module. If I ask for
   changes instead, make those changes and re-test before asking again.

MODULE LIST (build in this order):

Module 1 — Data ingestion + cleaning
  Load the six source tables, handle the known data-quality issues
  (footer rows, Indian comma-formatted numbers, missing/placeholder
  images, garbled regional-language text), extract work_id via regex,
  and join into the master lifecycle table.
  Test: show the joined table's shape, a sample of 10 joined rows, and
  counts of how many footer/malformed rows were caught and dropped.

Module 2 — Feature engineering
  All three granularities: work-level, vendor-level, MP/scheme-level
  (full feature list as specified earlier in this prompt).
  Test: show computed feature values for 5-10 real works, including at
  least one work that should score as clearly risky and one that
  shouldn't, so we can sanity-check the numbers by eye.

Module 3 — Rule engine (deterministic layer)
  1-year completion window, disallowed categories, allocation ceilings,
  SC/ST quota compliance.
  Test: show which real works trigger each rule, and confirm zero false
  triggers on a sample of clearly-compliant works.

Module 4 — Isolation Forest (unsupervised anomaly scoring)
  Test: show the distribution of anomaly scores, and the top 10
  highest-scored works with the feature values that likely drove it.

Module 5 — XGBoost + SMOTE (supervised risk scoring)
  Test: show model metrics (precision/recall on held-out labeled cases,
  including the real CAG-report cases used as ground truth), and risk
  probabilities for the same sample works used in Module 4.

Module 6 — SHAP explainability layer
  Test: show 3-5 full SHAP-generated explanation strings for real
  flagged works, and confirm they read as genuinely human-readable, not
  just a dump of feature names and numbers.

Module 7 — Composite Risk Score + tiers
  Exact formula: hard rule bypass to 80-100, else 40% Isolation Forest +
  40% XGBoost + 20% (vendor concentration + similarity averaged).
  Test: show the full score breakdown (each component + final score +
  tier) for 10 real works spanning Low/Medium/High.

Module 8 — Text similarity (duplicate/fake work detection)
  TF-IDF + cosine similarity, rapidfuzz for fast fuzzy matching.
  Test: show the highest-similarity pairs found in the real data, with
  both work descriptions side by side so we can judge if they're
  genuinely near-duplicates.

Module 9 — Perceptual image hashing
  Test: show any duplicate-image matches found in the real data (if the
  current export has usable images — if not, test against a synthetic
  pair of identical/near-identical images to prove the module works,
  and flag clearly that real-image validation is pending).

Module 10 — FastAPI backend (all five endpoints)
  Test: show a real request/response for each of the five endpoints
  against the real pipeline output.

Module 11 — PostgreSQL schema + persistence
  Test: show the schema (tables/columns), and confirm a round-trip —
  write a scored work, read it back, values match.

Module 12 — Frontend: District Authority case-queue screen (static mockup)
  Per the UI direction earlier in this prompt — dense data table, not
  cards. This is a MOCKUP for visual sign-off, not wired to real data yet.
  Test: show me the rendered screen. I will approve the direction or
  send it back for redesign before any interactivity is built.

Module 13 — Frontend: District Authority screen wired to real API
  Test: show it actually displaying real flagged works from Module 10's
  API, including the SHAP explanation panel with real data.

Module 14 — Frontend: remaining three role views (Ministry, State
  Nodal, MP transparency view)
  Test: show each one rendered with real, role-appropriate data.

Module 15 — Auditor feedback loop
  Clear/escalate/confirm actions persisted and available as labels for
  the next XGBoost retraining cycle.
  Test: show an action recorded via the API, then show it appearing in
  a query of "labeled cases available for retraining."

Do not reorder these modules, skip the test step, or bundle two modules
into one "for efficiency" — the whole point is that I can catch a wrong
assumption after Module 3 instead of after Module 14.