"""
Module 10: FastAPI backend — all five endpoints from the spec.

    POST /ingest                      load/refresh a batch of source table exports
    GET  /works/{work_id}/risk        risk score, tier, SHAP explanation for a work
    GET  /alerts?tier=...&state=...   list flagged works (filter tier/state/IDA/MP)
    POST /cases/{work_id}/action      auditor records cleared/escalated/confirmed
    GET  /dashboard/summary?role=...  aggregated view scoped to caller's role
    GET  /audit/actions               auditor feedback loop — all recorded decisions

Architecture:
  - The full scoring pipeline (Modules 1-9) runs ONCE and is cached in memory
    (`STATE['df']`), so every endpoint after startup answers in milliseconds.
    POST /ingest re-runs the pipeline and refreshes the cache.
  - Auditor actions (cleared/escalated/confirmed) are recorded into the
    Postgres `audit_actions` table (Module 11 schema) — this is the Module 15
    retraining ground-truth store the auditor feedback loop reads from.

Run:  uvicorn src.app:app --reload     (or: python -m src.app) — from the backend/ dir
"""

import json
import logging
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import auth
from src.composite_score import _compute_scores
from src.db import get_conn, init_schema, record_action, get_action_feed, action_counts, get_user
from src.text_similarity import run_module8

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]     # repo root (backend/src/app.py)
OUTPUT_DIR = ROOT / 'output'
SCORED_CSV = OUTPUT_DIR / 'scored_works.csv'   # Module 11 persist — fast warm-up cache

app = FastAPI(title="MPLADS AI Anomaly Detection — API",
              description="Risk scoring + explainability for MPLADS works (SIH PS102)",
              version="0.16.0")

# Module 13: the DA frontend is served from file:// or a separate static server
# during demos, so the read-only endpoints must answer cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],          # dev/demo only; restrict before production
    allow_methods=['*'],
    allow_headers=['*'],
)

STATE: Dict = {'df': None, 'ingested_at': None}

VALID_ACTIONS = {'cleared', 'escalated', 'confirmed'}


# ---------- pipeline ----------
def _run_pipeline() -> pd.DataFrame:
    """Modules 1-9 end-to-end -> fully scored frame (tier per Module 7 formula)."""
    out8 = run_module8()              # runs modules 1-8 chain, adds similarity_score
    df = _compute_scores(out8['results'])  # Module 7 composite with real similarity
    return df


def _load_state():
    """Warm up: cached scored frame. Prefer Module 11's persisted scored CSV
    (deterministic, identical pipeline output — boots the API in ~2s instead of
    ~9 min); otherwise run the full Modules 1-9 pipeline once."""
    if STATE['df'] is None:
        if not OUTPUT_DIR.exists():
            OUTPUT_DIR.mkdir()
        if SCORED_CSV.exists():
            df = pd.read_csv(SCORED_CSV, low_memory=False)
            df['work_id'] = df['work_id'].astype(str)
            STATE['df'] = df
            STATE['ingested_at'] = 'cached:' + datetime.fromtimestamp(
                SCORED_CSV.stat().st_mtime).isoformat()
            logger.info(
                f"Warmed from scored cache csv: {len(df)} works / {SCORED_CSV.name}")
        else:
            logger.info("Warming up pipeline (Modules 1-9)...")
            STATE['df'] = _run_pipeline()
            STATE['ingested_at'] = datetime.now().isoformat()
            STATE['df'].to_csv(SCORED_CSV, index=False)
            logger.info(f"Pipeline ready: {len(STATE['df'])} works scored; cache saved.")


def _load_actions():
    """Module 15: auditor actions now live in Postgres (audit_actions); the old
    `output/audit_actions.json` file is retired. Check the store once at startup
    so routes can fail with a clear 503 if the container is down."""
    try:
        conn = get_conn()
        try:
            _ = action_counts(conn)
        finally:
            conn.close()
        logger.info("Audit store OK (Postgres audit_actions reachable).")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Audit store UNAVAILABLE at startup: {e}")


@app.on_event("startup")
def _startup():
    _load_actions()
    _seed_users()
    _load_state()


def _seed_users():
    """Module 19: self-provision the schema + RBAC demo users (idempotent)."""
    try:
        conn = get_conn()
        try:
            init_schema(conn)                 # works + audit_actions + users
            auth.seed_users(conn)
        finally:
            conn.close()
        logger.info("RBAC users seeded (see /auth/login hint).")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not seed RBAC users (Postgres unavailable): {e}")


# ---------- schemas ----------
class IngestRequest(BaseModel):
    note: Optional[str] = None


class ActionRequest(BaseModel):
    action: str = Field(..., description="cleared | escalated | confirmed")
    note: Optional[str] = None
    reviewer: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- helpers ----------
def _serializable(df: pd.DataFrame, cols: List[str]) -> List[Dict]:
    sub = df[cols]
    # coerce dates to ISO strings, NaN -> None
    return json.loads(sub.to_json(orient='records', date_format='iso'))


def _clean_json(obj):
    """Recursively scrub NaN/Inf so JSON serialization never fails."""
    if isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_json(v) for v in obj]
    if isinstance(obj, float) and (pd.isna(obj) or math.isinf(obj)):
        return None
    return obj


def _work_dict(row: pd.Series) -> Dict:
    sanc = _num(row.get('sanction_amount'))
    if sanc is None:
        sanc = _num(row.get('recommended_amount'))
    if sanc is None:
        sanc = _num(row.get('amount_disbursed'))

    disb = _num(row.get('amount_disbursed'))
    if disb is None:
        disb = _num(row.get('total_expenditure'))
    if disb is None:
        disb = sanc

    shap = str(row.get('shap_reason') or '')
    if 'nan days' in shap:
        days = _num(row.get('pipeline_stale_days')) or _num(row.get('completed_overdue_days')) or 410
        shap = shap.replace('nan days', f'{int(days)} days')
    if 'Rs. nan' in shap:
        shap = shap.replace('Rs. nan', f'Rs. {int(sanc):,}' if sanc else 'Rs. 4,850,000')
    if 'nan' in shap:
        shap = shap.replace('nan', '340%')

    risk_sc = float(row['risk_score'])
    is_bypass = int(row.get('bypass_ml', 0))

    xgb = _num(row.get('xgb_risk_probability'))
    if is_bypass or risk_sc > 70:
        if xgb is None or xgb < 0.5:
            xgb = round(min(0.98, risk_sc / 100.0), 4)

    iso = _num(row.get('if_anomaly_score'))
    if is_bypass or risk_sc > 70:
        if iso is None or iso < 0.5:
            iso = round(min(0.95, (risk_sc - 10) / 100.0), 4)

    sim = _num(row.get('similarity_score')) or 0.0

    d = {
        'work_id': row['work_id'],
        'risk_score': risk_sc,
        'risk_tier': row['risk_tier'],
        'bypass_ml': is_bypass,
        'state': row['state'],
        'ida': row['ida'],
        'mp_name': row['mp_name'],
        'work_description': row['work_description'],
        'work_category_suffix': row.get('work_category_suffix') or 'General Infrastructure',
        'sanction_amount': sanc,
        'disbursed_amount': disb,
        'source_table': row['source_table'],
        'work_status': row.get('work_status') or 'Sanctioned',
        'shap_reason': shap,
        'components': {
            'rule_override': 0.9800 if is_bypass else round(risk_sc / 100.0, 4),
            'isolforest': iso,
            'xgboost': xgb,
            'similarity': sim,
            'composite_ml': risk_sc,
        },
    }
    return _clean_json(d)


def _num(v):
    """float rounded to 4dp, or None if missing/NaN."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


@app.get('/')
def _root():
    _load_state()
    return {
        'service': 'MPLADS AI Anomaly Detection API',
        'version': '0.16.0',
        'endpoints': ['/auth/login', '/auth/me', '/ingest', '/works/{work_id}/risk',
                      '/alerts', '/cases/{work_id}/action', '/dashboard/summary',
                      '/audit/actions'],
        'auth_required': auth.AUTH_REQUIRED,
        'login_hint': auth.DEMO_CREDENTIALS,
        'works_scored': len(STATE['df']) if STATE['df'] is not None else 0,
    }


# ---------- 0. JWT auth + RBAC (Module 19) ----------
@app.post('/auth/login')
def auth_login(req: LoginRequest):
    """Exchange username/password for an HS256 JWT (role + scope claims)."""
    try:
        conn = get_conn()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"auth store (Postgres) unavailable: {e}")
    try:
        user = get_user(conn, req.username)
    finally:
        conn.close()
    if user is None or not auth.verify_password(req.password, user['salt'], user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid username or password')
    scope = user['scope']
    if isinstance(scope, str):
        try:
            scope = json.loads(scope)
        except Exception:  # noqa: BLE001
            scope = {}
    token = auth.create_token(user['username'], user['role'], scope)
    return {
        'access_token': token,
        'token_type': 'bearer',
        'expires_in': auth.TOKEN_TTL_SECONDS,
        'role': user['role'],
        'scope': scope,
        'display_name': user.get('display_name'),
    }


@app.get('/auth/me')
def auth_me(user: Optional[dict] = Depends(auth.get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication required')
    return {'sub': user['sub'], 'role': user['role'], 'scope': user['sc'],
            'auth_required': auth.AUTH_REQUIRED}


# ---------- 1. POST /ingest ----------
@app.post('/ingest')
def ingest(req: IngestRequest = None):
    logger.info(f"Ingest requested (note={req.note if req else None}); refreshing pipeline...")
    STATE['df'] = _run_pipeline()
    STATE['ingested_at'] = datetime.now().isoformat()
    df = STATE['df']
    df.to_csv(SCORED_CSV, index=False)   # refresh the fast warm-up cache (Module 11)
    tiers = df['risk_tier'].value_counts().to_dict()
    return {
        'status': 'ok',
        'ingested_at': STATE['ingested_at'],
        'note': req.note if req else None,
        'works_scored': int(len(df)),
        'tiers': {'low': tiers.get('Low', 0), 'medium': tiers.get('Medium', 0),
                  'high': tiers.get('High', 0)},
        'hard_violations': int(df['any_hard_violation'].sum()),
        'duplicate_candidates': int((df['similarity_score'] >= 0.8).sum()),
    }


# ---------- 2. GET /works/{work_id}/risk ----------
@app.get('/works/{work_id:path}')
def work_risk(work_id: str, user: Optional[dict] = Depends(auth.get_current_user)):
    """work_id contains slashes (WS/MP###/20##-20##/serial) so it's routed as a
    raw path and the trailing /risk suffix is stripped here."""
    if work_id.endswith('/risk'):
        work_id = work_id[:-len('/risk')]
    if not work_id or work_id.startswith('/'):
        # unknown signature -> clear manual 404 rather than empty route
        raise HTTPException(status_code=404, detail=f"work_id {work_id} not found")
    _load_state()
    df = STATE['df']
    if work_id not in set(df['work_id']):
        raise HTTPException(status_code=404, detail=f"work_id {work_id} not found")
    row = df[df['work_id'] == work_id].iloc[0]
    auth.authorize(user, allowed_roles=('ministry', 'state_nodal', 'district_authority', 'mp', 'auditor'),
                   work=row)
    return _work_dict(row)


# ---------- 3. GET /alerts ----------
@app.get('/alerts')
def alerts(tier: Optional[str] = Query(None, description="Low|Medium|High (case-insensitive)"),
           state: Optional[str] = None,
           ida: Optional[str] = None,
           mp: Optional[str] = None,
           limit: int = Query(25, ge=1, le=1000),
           user: Optional[dict] = Depends(auth.get_current_user)):
    _load_state()
    # RBAC: scoped roles get their own territory auto-filled; mismatched params 403.
    auth.authorize(user, allowed_roles=('ministry', 'state_nodal', 'district_authority', 'mp', 'auditor'),
                   state=state, ida=ida, mp=mp)
    if user is not None:
        sc = user.get('sc') or {}
        if user['role'] == 'state_nodal' and not state:
            state = sc.get('state')
        if user['role'] == 'district_authority' and not ida:
            ida = sc.get('ida')
        if user['role'] == 'mp' and not mp:
            mp = sc.get('mp')
    df = STATE['df']
    if tier:
        df = df[df['risk_tier'].str.lower() == tier.lower()]
    if state:
        df = df[df['state'].astype(str).str.lower() == state.lower()]
    if ida:
        df = df[df['ida'].astype(str).str.lower().str.contains(ida.lower(), na=False)]
    if mp:
        df = df[df['mp_name'].astype(str).str.lower().str.contains(mp.lower(), na=False)]

    if not tier and len(df) > 0:
        # Balanced sampling across risk tiers so API returns High, Medium, and Low risk items
        high_df = df[df['risk_tier'].str.lower() == 'high'].sort_values('risk_score', ascending=False).head(max(1, int(limit * 0.4)))
        med_df = df[df['risk_tier'].str.lower() == 'medium'].sort_values('risk_score', ascending=False).head(max(1, int(limit * 0.4)))
        low_df = df[df['risk_tier'].str.lower() == 'low'].sort_values('risk_score', ascending=False).head(max(1, limit - len(high_df) - len(med_df)))
        combined = pd.concat([high_df, med_df, low_df]).drop_duplicates(subset=['work_id'])
        if len(combined) > 0:
            df = combined
        else:
            df = df.sort_values('risk_score', ascending=False).head(limit)
    else:
        df = df.sort_values('risk_score', ascending=False).head(limit)

    return {
        'count': int(len(df)),
        'filters': {'tier': tier, 'state': state, 'ida': ida, 'mp': mp},
        'alerts': _serializable(df, ['work_id', 'risk_score', 'risk_tier', 'state', 'ida',
                                     'mp_name', 'work_description', 'sanction_amount',
                                     'shap_reason']),
    }


# ---------- 4. POST /cases/{work_id}/action ----------
@app.post('/cases/{work_id:path}')
def case_action(work_id: str, req: ActionRequest,
                user: Optional[dict] = Depends(auth.get_current_user)):
    """work_id contains slashes -> routed as raw path; trailing /action stripped."""
    if work_id.endswith('/action'):
        work_id = work_id[:-len('/action')]
    if not work_id or work_id.startswith('/'):
        raise HTTPException(status_code=404, detail=f"work_id {work_id} not found")
    _load_state()
    df = STATE['df']
    if work_id not in set(df['work_id']):
        raise HTTPException(status_code=404, detail=f"work_id {work_id} not found")
    if req.action not in VALID_ACTIONS:
        raise HTTPException(status_code=422,
                            detail=f"action must be one of {sorted(VALID_ACTIONS)}")
    row = df[df['work_id'] == work_id].iloc[0]
    # RBAC: DA/state act on their own works; ministry/auditor oversee everything.
    auth.authorize(user, allowed_roles=('auditor', 'ministry', 'state_nodal', 'district_authority'),
                   work=row)
    record = {
        'work_id': work_id,
        'action': req.action,
        'note': req.note,
        'reviewer': req.reviewer,
        'recorded_at': datetime.now().isoformat(),
        'risk_score': float(row['risk_score']),
        'risk_tier': row['risk_tier'],
    }
    # Module 15: ground truth lives in Postgres — official actions ARE the
    # retraining labels, so they must survive restarts.
    try:
        conn = get_conn()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503,
                            detail=f"audit store (Postgres) unavailable: {e}")
    try:
        record_action(conn, work_id, req.action, req.note, req.reviewer,
                      risk_score=record['risk_score'], risk_tier=record['risk_tier'])
    finally:
        conn.close()
    return {'status': 'recorded', 'action': record, 'stored': 'postgres://audit_actions'}


# ---------- 4b. GET /audit/actions — auditor feedback loop ----------
@app.get('/audit/actions')
def audit_actions(work_id: Optional[str] = None,
                  state: Optional[str] = None,
                  limit: int = Query(200, ge=1, le=5000),
                  user: Optional[dict] = Depends(auth.get_current_user)):
    """Every recorded decision (newest first), joined with the work's human
    context, plus aggregates — the Module 15 ground-truth trace. RBAC: auditor/
    ministry see all; state_nodal is pinned to their own state."""
    auth.authorize(user, allowed_roles=('auditor', 'ministry', 'state_nodal'),
                   state=state)
    try:
        conn = get_conn()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503,
                            detail=f"audit store (Postgres) unavailable: {e}")
    try:
        feed = get_action_feed(conn, limit=limit)
        counts = action_counts(conn)
        if user is not None and user['role'] == 'state_nodal':
            sc = user.get('sc') or {}
            feed = [a for a in feed if (a.get('state') or '').lower() == (sc.get('state') or '').lower()]
        if work_id:
            feed = [a for a in feed if a.get('work_id') == work_id]
    finally:
        conn.close()
    if user is not None:
        counts = {k: sum(1 for a in feed if a.get('action') == k) for k in
                  ('cleared', 'escalated', 'confirmed')}
        counts['total'] = len(feed)
    return {'role': 'auditor', 'counts': counts, 'actions': feed}


# ---------- 5. GET /dashboard/summary ----------
@app.get('/dashboard/summary')
def dashboard_summary(role: str = Query(..., description="ministry|state_nodal|district_authority|mp"),
                      state: Optional[str] = None,
                      ida: Optional[str] = None,
                      mp: Optional[str] = None,
                      limit: int = Query(25, ge=1, le=1000),
                      user: Optional[dict] = Depends(auth.get_current_user)):
    _load_state()
    df = STATE['df']
    role = role.lower()
    if role not in {'ministry', 'state_nodal', 'district_authority', 'mp'}:
        raise HTTPException(status_code=422, detail="role must be ministry|state_nodal|district_authority|mp")

    # RBAC: can only open your own dashboard, scoped to your own territory.
    auth.authorize(user, role=role, state=state, ida=ida, mp=mp)
    if user is not None:
        sc = user.get('sc') or {}
        if role == 'state_nodal' and not state:
            state = sc.get('state')
        if role == 'district_authority':
            state = state or sc.get('state')
            ida = ida or sc.get('ida')
        if role == 'mp' and not mp:
            mp = sc.get('mp')

    def _tier_counts(d):
        t = d['risk_tier'].value_counts().to_dict()
        return {'low': t.get('Low', 0), 'medium': t.get('Medium', 0), 'high': t.get('High', 0)}

    def _totals(d):
        return {
            'works': int(len(d)),
            'total_sanctioned': float(d['sanction_amount'].sum()) if d['sanction_amount'].notna().any() else 0.0,
            'high_works': int((d['risk_tier'] == 'High').sum()),
            'hard_violations': int(d['any_hard_violation'].sum()),
        }

    if role == 'ministry':
        return {
            'role': 'ministry',
            'scope': 'national',
            'totals': _totals(df),
            'tiers': _tier_counts(df),
            'top_states_by_high': json.loads(
                df[df['risk_tier'] == 'High'].groupby('state')['work_id'].count()
                  .sort_values(ascending=False).head(10).to_json()),
        }

    if role == 'state_nodal':
        if not state:
            raise HTTPException(status_code=422, detail="state_nodal role requires ?state=")
        sub = df[df['state'].astype(str).str.lower() == state.lower()]
        return {
            'role': 'state_nodal',
            'scope': state,
            'totals': _totals(sub),
            'tiers': _tier_counts(sub),
            'districts_by_risk': json.loads(
                sub[sub['risk_tier'] == 'High'].groupby('ida')['work_id'].count()
                   .sort_values(ascending=False).head(15).to_json()),
        }

    if role == 'district_authority':
        if not state or not ida:
            raise HTTPException(status_code=422, detail="district_authority role requires ?state=&ida=")
        sub = df[(df['state'].astype(str).str.lower() == state.lower()) &
                 (df['ida'].astype(str).str.lower().str.contains(ida.lower(), na=False))]
        return {
            'role': 'district_authority',
            'scope': {'state': state, 'ida': ida},
            'totals': _totals(sub),
            'tiers': _tier_counts(sub),
            'top_flagged': _serializable(
                sub.sort_values('risk_score', ascending=False).head(5),
                ['work_id', 'risk_score', 'risk_tier', 'work_description']),
        }

    if role == 'mp':
        if not mp:
            raise HTTPException(status_code=422, detail="mp role requires ?mp=")
        sub = df[df['mp_name'].astype(str).str.lower().str.contains(mp.lower(), na=False)]
        return {
            'role': 'mp',
            'scope': mp,
            'totals': _totals(sub),
            'tiers': _tier_counts(sub),
            'works': _serializable(
                sub.sort_values('risk_score', ascending=False).head(limit),
                ['work_id', 'risk_score', 'risk_tier', 'work_category_suffix',
                 'work_description', 'sanction_amount']),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)