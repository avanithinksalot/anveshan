# Session Log — 2026-09-14 (Modules 13–18: core build + tech-stack alignment)

Companion to `log.md`. This file captures the *current* working session in
detail; `log.md` holds the authoritative project-wide status and module history.

---

## Session goal

Take the MPLADS AI MVP from "DA case-queue mockup approved" (Module 12) through
the remaining build spec, then audit the whole platform against `build prompt.md`.

## What was accomplished this session

### Module 13 — District Authority screen wired to the real API ✅
- `src/app.py` v0.13.0: CORS middleware (dev/demo `*`), fast boot from
  `output/scored_works.csv` cache (~2s vs ~9-min pipeline), `/ingest` refreshes
  the cache CSV.
- `frontend/da_app.html`: interactive DA console — live stat strip, 50-row case
  queue (`/alerts?ida=bareilly`), SHAP detail panel with real reasons, and
  clear/escalate/confirm actions with toast.
- Verified headless via Edge DOM capture: exactly 50 rows == API count; detail
  panel auto-populated with real payload (bypass 81.7/60.7, real SHAP sentence).

### Module 14 — Ministry, State Nodal, MP transparency views ✅
- `src/gen_role_views.py` — shared-CSS generator emitting self-contained
  `frontend/ministry_view.html`, `state_nodal_view.html`, `mp_view.html`.
- API fix found by testing: `/dashboard/summary?role=mp` hard-coded
  `.head(25)` → added `limit` param (default 25, cap 1000); app.py v0.14.0.
  MP view now shows all 307 works.
- Headless verification PASS (driven real clicks via `#test` hash hook):
  - ministry: 48,925 · ₹7.37B · 2,918 High · 2,749 breaches · 10 states · 12 alert rows
  - state nodal (UP): 11,601 · ₹2.06B · 1,394 High · 1,374 breaches · 16 districts
  - mp (Shri Hardeep Singh Puri): 307 · ₹14.3M · 2 High · all 307 works

### Module 15 — Auditor feedback loop (Postgres-backed ground truth) ✅
- `src/db.py` additions: `get_action_feed` (decision × works LEFT JOIN),
  `action_counts` (GROUP BY action).
- `src/app.py` v0.15.0: `POST /cases/{id}/action` now writes to Postgres
  `audit_actions` (JSON file retired); new `GET /audit/actions` returns the full
  decision feed with work context + aggregates; 503 with clear message if the
  container is down; startup only logs a warning.
- `frontend/auditor_view.html` + `da_app.html` badge restore from `/audit/actions`
  on load — both views agree on ground truth.
- Real bug found + fixed by DOM test: auditor rows were injected without a
  `<table>` wrapper → browser flattened the `<td>`s; wrapped in
  `<table><tbody>`.
- Live round-trip verified: POST cleared/escalated/confirmed → DB count
  1 → 4 → `/audit/actions` returns all 4 with joined context → auditor view
  renders 4 rows (stat strip 4/1/2/1) → DA console reload shows badges from DB.

### Tech-stack audit vs `build prompt.md`
- Re-read the master prompt; logged full gap analysis in `log.md` CURRENT STATE.
- **MATCH:** Python/pandas/numpy, sklearn (IsolationForest), XGBoost, SMOTE,
  SHAP, TF-IDF+rapidfuzz, imagehash+Pillow, FastAPI/Uvicorn/Pydantic, the five
  spec endpoints (+bonus), composite formula / bypass / tiers.
- **GAP:** (1) Frontend is vanilla static HTML/JS — spec wants React + Tailwind
  CSS + Recharts/D3 (incl. a Ministry D3 vendor-network graph);
  (2) `src/db.py` uses raw psycopg2 — spec wants SQLAlchemy;
  (3) JWT + RBAC auth not built; (4) no app Dockerfile / docker-compose.
- **UI conflict:** build prompt bans glassmorphism/gradients/glow blobs and
  wants a restrained palette; `looks.md` uses those (density, IBM Plex, and
  tier-only color already comply).
- Three scoping questions (frontend scope, visual direction, auth timing) were
  asked via the question tool and **dismissed by the user** — left pending in
  `log.md`.

## Commands / patterns that worked this session (Windows PowerShell 5.1)

```powershell
# boot the API (background, logs to output/)
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*src.app*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -FilePath python -ArgumentList '-m','src.app' `
  -RedirectStandardOutput output/uvicorn.log `
  -RedirectStandardError output/uvicorn.err.log -WindowStyle Hidden

# headless frontend verification (Edge)
$edge="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
& $edge --headless=new --disable-gpu --virtual-time-budget=16000 --dump-dom `
  "file:///D:/IDEs/Visual Studio Code/SIH PS102 MVP/frontend/auditor_view.html" 2>$null |
  Out-File -Encoding utf8 output/dom15_auditor.html
```

Gotchas logged: inline `<script>` template literals match DOM regexes
(`$(`{esc(...)`` strings) — always filter them via `${`-exclusion or exact
value matching; `₹` mojibake in dumps is an Edge→PowerShell UTF-8 artifact, the
shipped pages are fine; bare `<td>` inside `innerHTML` without a `<table>`
wrapper is silently flattened by browsers.

## Live environment state (end of session)

- API running on `127.0.0.1:8000` (app.py v0.15.0 — endpoints unchanged by the
  SQLAlchemy layer; API restarted on the new `src/db.py` after Module 16).
- Postgres container `mplads-pg` up: 48,924 works; 7 audit_actions rows
  (incl. the Module 16 live-check `escalated` on `WS/MP019/2025-2026/164907`).
- **React SPA** `webapp/` on `http://localhost:4173` (vite preview, 5 routes:
  `/da` `/ministry` `/state-nodal` `/mp` `/auditor`); build = `npm run build`,
  dev = `npm run dev`. Vanilla HTML views kept intact in `frontend/`.
- Node v24.14.1, npm 11.11.0; deps: react 19, react-router-dom 7, tailwindcss 4
  (`@tailwindcss/vite`), recharts 3, d3 7 + @types/d3; Python SQLAlchemy 2.0.52.
- Todos: Modules 3–16 + 17 + 18 `completed`; README/runbook + deferred items
  (JWT/RBAC, Docker artifacts, lazy code-split) pending.

## Open items / next session

1. README/runbook + final demo pass.
2. Deferred stack items (documented in `log.md`): JWT + RBAC auth, Docker
   artifacts (API + web Dockerfile/docker-compose), optional bundle code-split,
   optional migration of `frontend/*.html` launch options to the SPA.
3. Long-standing: Module 9 real-image validation PENDING (export ships no real
   images); Module 5 metrics optimistic until Module 15 ground truth is used
   for retraining; `work_status_stage_duration` end-date fix.

## Module 16–18 detail (this session's alignment build)

### Module 16 — SQLAlchemy 2.0 Core in `src/db.py` ✅ (20/20 test PASS + live)
- `create_engine('postgresql+psycopg2://...', pool_pre_ping=True)`;
  `get_conn()` → `engine.connect()`; all public signatures unchanged.
- `init_schema` splits DDL on `;`.
- **Timing fix:** SQLAlchemy `executemany()` = row-by-row → 48,924-row upsert
  timed out at 180s. Replaced with `psycopg2.extras.execute_batch` on
  `conn.connection` (page_size=2000, `%s`, explicit `(cols)=%s`). Now ~10–15 s.
- **Shape fix:** after `.mappings()`, rows are already `RowMapping`; the old
  `dict(row._mapping)` raised `NoSuchColumnError` → `_row_dict` is now `dict(row)`.
- New `delete_actions(conn, work_id)`; test_db cleanup uses it.
- Verify: `python -m src.test_db` → 20 passed, 0 failed; live POST
  `escalated` on `WS/MP019/2025-2026/164907` → `stored= postgres://audit_actions`.

### Module 17 — React SPA (webapp/) ✅
- Scaffold: `npm create vite webapp -- --template react-ts`; Tailwind 4 via
  `@tailwindcss/vite`; Router7; Recharts 3; d3 7.
- Theme in `src/index.css` via `@theme` tokens: `--color-base #0e1420`,
  panel #131b2c, edge #223048, fg #e6eaf2, tier low/med/high #3fb950/#d29922/#f85149,
  IBM Plex fonts. Build-prompt-compliant (no glass/gradients/blobs; risk tier
  colors reserved for risk only).
- Views (all live-API): `/da` (50 BAREILLY rows, SHAP + actions → Postgres,
  actioned badges), `/ministry` (Recharts bar + donut, D3 force network 50
  nodes), `/state-nodal` (11,601, district bars + drill, 25 rows), `/mp` (307
  via `mp=Hardeep&limit=1000`, ₹14,31,83,528), `/auditor` (7 rows, 5s poll).

### Module 18 — build + headless verify ✅
- `npm run build` (tsc -b && vite build) clean; only >500 KB chunk warning.
- TS fixes during build: JSX `{{id}}` → `&#123;` (parsed as object literal),
  unused imports, D3 `SimulationNodeDatum`/`SimulationLinkDatum` generics,
  `return () => sim.stop()` must be a block.
- Verified headless Edge (virtual-time-budget=9000) per route — all real data +
  no API banners. Dumps in `output/react_dom_{route}_3.html`.
- API-contract gotchas caught by route dumps: `role=mp` → 422 without `?mp=`;
  `/alerts?ida=` only matches exact stored spelling (e.g. PRAYAGRAJ has 119 High
  alerts; JAUNPUR has 0 — district drilldown derived from the alert feed itself).

## SAVE POINT (resume here) — Module 19 stack finalization, 2026-09-14

**User directive:** forget/ignore `looks.md` (deleted); `build prompt.md` is the
only authority. Frontend must be DYNAMIC (React SPA), not static HTML. Keep only
files important to the prototype; keep the stack per `build prompt.md`.

### FEB 19 follow-up — Accuracy report ✅ (2026-09-14)

- User asked "what is the accuracy of the model" → answered from log.md:
  XGB held-out (n=9,785) accuracy **99.87%** (P 99.54 / R 98.47 / F1 99.00 /
  AUC 0.992), plus the honest caveat that labels are DERIVED (rule engine + IF
  outputs are also model features) so real-world accuracy is pending auditor
  ground truth.
- User requested "an accuracy report in report.txt with complete accuracy" →
  created `report.txt` at project root: executive summary, model stack +
  composite formula, tier-level breakouts, full XGB confusion-matrix metrics,
  IF calibration, text/image detectors, honest limitations (derived labels,
  class imbalance, no GT yet, auditor-loop path to true accuracy), verification
  evidence table.

### Module 19 — COMPLETED ✅ (2026-09-14)

1. **Reorg:** `src/` → `backend/src/` (PEP-420 namespace pkg). Run backend from
   `backend/`. Re-ran **test_db 20/20 PASS** post-move.
2. **JWT + RBAC (build-prompt TECH STACK):**
   - `backend/src/auth.py`: PyJWT 2.14 HS256, PBKDF2-HMAC-SHA256 passwords,
     `get_current_user` dependency, fail-closed `authorize()`, `AUTH_REQUIRED=0`
     demo vs `=1` enforced. 5 demo users seeded.
   - `db.py`: `users` table + `upsert_user`/`get_user`.
   - `app.py` v0.16.0: `/auth/login`, `/auth/me`, RBAC guards on all protected
     endpoints. Startup self-provisions schema + seeds users.
   - **Key fix:** psycopg2 can't adapt dict for jsonb — changed
     `scope=(scope or {})` → `scope=json.dumps(scope or {})`.
3. **RBAC matrix: ALL GREEN** (5×200 logins, 403s at wrong-role/out-of-scope,
   401 on bad/garbage token, 200 on anonymous demo, auditor feed 200).
4. **SPA dynamic auth:** LoginView + apiFetch + ?token= bootstrap + RequireAuth
   + RoleGate + role-filtered nav + sign-out. All 5 views migrated from bare
   fetch to apiFetch (zero localhost hard-codes).
5. **Headless SPA verify: ALL GREEN** (login form, 5 role routes with real data,
   cross-role guard redirects correctly).
6. **Pruned:** `frontend/`, `gen_mockup.py`, `gen_role_views.py` deleted.
7. **Docker stack:** Dockerfiles (api + web), nginx.conf, docker-compose.yml
   (db/api/web), .env.example, .gitignore. Both images build. Config valid.
8. **README.md:** runbook (local + docker), demo creds, API surface, env vars,
   tech stack table vs build prompt.

### Final state on disk

- `backend/src/` — 15 modules (app, auth, db, composite_score, data_ingestion,
  feature_engineering, image_hashing, isolation_forest, rule_engine,
  shap_explain, text_similarity, xgboost_model, test_db, test_api,
  verify_everything)
- `webapp/src/` — api.ts, types.ts, App.tsx, main.tsx, index.css, vite-env.d.ts,
  components/UI.tsx, components/DetailPanel.tsx, views/{Login,DA,Ministry,
  StateNodal,MP,Auditor}View.tsx
- `backend/Dockerfile`, `webapp/Dockerfile`, `webapp/nginx.conf`,
  `docker-compose.yml`, `.env.example`, `.gitignore`, `README.md`

### Verification evidence

| Check | Status |
|---|---|
| python -m src.test_db | 20/20 PASS |
| python -m src.test_api | 15/15 (200/404/422) |
| npm run build | Clean (>500 KB chunk warning) |
| RBAC matrix | ALL GREEN |
| Headless SPA | 6 routes + cross-role guard |
| docker compose config | VALID |
| docker build (api + web) | SUCCESS |