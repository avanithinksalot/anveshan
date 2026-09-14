# MPLADS AI — Anomaly Detection Console (Smart India Hackathon PS102 MVP)

Privacy-aware, ML-assisted risk triage for the Members of Parliament Local Area
Development Scheme (MPLADS). A FastAPI + PostgreSQL backend scores every work
item for anomalies (cost inflation, duplicate billing, rule breaches, image
irregularities) and surfaces them to five role-scoped dashboards built as a
React SPA.

Full build log in [`log.md`](log.md); session notes in [`session.md`](session.md).
UI/UX authority: [`build prompt.md`](build prompt.md).

---

## Tech stack (matches `build prompt.md`)

| Layer | Choice | Where |
|---|---|---|
| ETL/tabular | Python + pandas + numpy | `backend/src/data_ingestion.py`, `feature_engineering.py` |
| Unsupervised anomaly | scikit-learn IsolationForest | `backend/src/isolation_forest.py` |
| Supervised model | XGBoost (SMOTE-resampled) | `backend/src/xgboost_model.py` |
| Explainability | SHAP | `backend/src/shap_explain.py`, `composite_score.py` |
| Duplicate text | TF-IDF + rapidfuzz | `backend/src/text_similarity.py` |
| Image forensics | imagehash + Pillow | `backend/src/image_hashing.py` |
| Hard rules | rubric engine | `backend/src/rule_engine.py` |
| API | FastAPI + Uvicorn + Pydantic | `backend/src/app.py` |
| Storage | PostgreSQL + SQLAlchemy 2 | `backend/src/db.py` |
| Auth | JWT (PyJWT) + RBAC | `backend/src/auth.py`, `auth.py` guards |
| Frontend | React 19 + TS + Vite + Tailwind 4 | `webapp/` |
| Charts | Recharts (bar/donut) + D3 (force graph) | `webapp/src/views/MinistryView.tsx` |
| Deployment | Docker + docker-compose | `Dockerfile`s, `docker-compose.yml` |

---

## Quick start

Prereqs: Python 3.12+, Node 20+, PostgreSQL 16 (or Docker), `compact` not needed.

### 1. Backend (local)

```bat
cd backend
python -m pip install -r requirements.txt
set DATABASE_DSN=postgresql+psycopg2://mplads:mplads@localhost:5432/mplads
python -m src.app
```

Server :8000. Schema (works, audit_actions, users) is self-provisioned at
startup, and RBAC demo users are seeded.

### 2. Frontend (local)

```bat
cd webapp
set VITE_API_BASE=http://localhost:8000
npm install
npm run dev        # dev on :5173
npm run build      # prod build -> dist/
npm run preview    # serve dist on :4173
```

### 3. Docker (everything)

```bat
copy .env.example .env
docker compose up --build
```

- Web: http://localhost:4173  (nginx SPA)
- API: http://localhost:8000  (docs at /docs)
- Postgres: localhost:5432

Mount `/data/datasets` (read-only) for ingestion; the `/app/output` volume keeps
the scored-cache + logs warm.

---

## Demo accounts (RBAC)

| Role | View | Username | Password |
|---|---|---|---|
| Ministry (national) | `/ministry` | `ministry` | `ministry@123` |
| State Nodal (UP) | `/state-nodal` | `up_nodal` | `up@nodal123` |
| District Authority (BAREILLY) | `/da` | `da_bareilly` | `bareilly@123` |
| MP (Shri H.S. Puri) | `/mp` | `mp_hardeep` | `hardeep@123` |
| Auditor | `/auditor` | `auditor` | `audit@mspi123` |

`AUTH_REQUIRED=0` (default) = open demo mode — anonymous browsing allowed, but
verified tokens still get role/scope enforcement. Set `AUTH_REQUIRED=1` to
require a sign-in for every route.

---

## API surface (FastAPI)

```
POST /auth/login            -> { access_token, role, scope }
GET  /auth/me               -> current user + claims
GET  /dashboard/summary     ?role=…&state=…&ida=…&mp=…&limit=…
GET  /alerts                ?state=…&ida=…&tier=…&limit=…
GET  /works/{work_id}/risk  full SHAP + rule breakdown
POST /cases/{work_id}/action { action: cleared|escalated|confirmed }
GET  /audit/actions         ?limit=…  (auditor ground-truth feed)
```

Conventions: `role=mp` requires `mp=` (substring match, e.g. `Hardeep`);

---

## Verification

```bat
cd backend
python -m src.test_db          # 20 SQLAlchemy checks -> 20 PASS
python -m src.test_api         # live API round-trip checks
python -m src.verify_everything # pipeline-wide module assertions
```

## Env vars

| Var | Default | Meaning |
|---|---|---|
| `DATABASE_DSN` | `postgresql+psycopg2://mplads:mplads@localhost:5432/mplads` | SQLAlchemy DSN |
| `JWT_SECRET` | `dev-insecure-change-me` | HS256 signing key (prod: override) |
| `JWT_TTL_SECONDS` | `43200` | token lifetime |
| `AUTH_REQUIRED` | `0` | `1` = JWT mandatory on all routes |
| `MPLADS_DATA_DIR` | absolute datasets path | ingestion source |
| `VITE_API_BASE` | `http://localhost:8000` | frontend→API base URL |
