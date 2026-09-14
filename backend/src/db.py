"""Module 16 — SQLAlchemy migration of the Module 11 persistence layer.

Same public API and same tables as the original psycopg2 implementation, now on
SQLAlchemy 2.0 Core (text()/executemany) with the psycopg2 driver under the
hood. Matches the `build prompt.md` TECH STACK: "PostgreSQL, SQLAlchemy".

Functions keep their original signatures so `src/app.py` and `src/test_db.py`
call sites are unchanged (only the test's one raw-cursor block moves to
`delete_actions`).

Connection uses env vars with localhost defaults (the mplads Docker container):
  MPLADS_PGHOST / MPLADS_PGPORT / MPLADS_PGUSER / MPLADS_PGPASSWORD / MPLADS_PGDB
"""

import json
import os
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd
import psycopg2.extras
from sqlalchemy import create_engine, text

PGHOST = os.getenv('MPLADS_PGHOST', 'localhost')
PGPORT = int(os.getenv('MPLADS_PGPORT', '5432'))
PGUSER = os.getenv('MPLADS_PGUSER', 'mplads')
PGPASSWORD = os.getenv('MPLADS_PGPASSWORD', 'mplads')
PGDB = os.getenv('MPLADS_PGDB', 'mplads')

# SQLAlchemy 2.0 engine; `get_conn()` returns a Connection (context-managed
# transaction autobegin; callers commit explicitly, exactly as before).
engine = create_engine(
    f'postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDB}',
    pool_pre_ping=True)


# Columns stored explicitly (well-known, queried by role scoping / alerts);
# everything else in the scored frame rides along in the `extra` JSONB.
EXPLICIT_COLS = [
    'work_id', 'risk_score', 'risk_tier', 'bypass_ml', 'state', 'ida',
    'mp_name', 'mp_party', 'constituency', 'work_description',
    'work_category_suffix', 'sanction_amount', 'source_table', 'work_status',
    'if_anomaly_score', 'xgb_risk_probability', 'similarity_score',
    'composite_ml_score', 'shap_reason',
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    work_id                 TEXT PRIMARY KEY,
    risk_score              NUMERIC NOT NULL,
    risk_tier               TEXT    NOT NULL CHECK (risk_tier IN ('Low','Medium','High')),
    bypass_ml               BOOLEAN NOT NULL,
    state                   TEXT,
    ida                     TEXT,
    mp_name                 TEXT,
    mp_party                TEXT,
    constituency            TEXT,
    work_description        TEXT,
    work_category_suffix    TEXT,
    sanction_amount         NUMERIC,
    source_table            TEXT,
    work_status             TEXT,
    if_anomaly_score       NUMERIC,
    xgb_risk_probability   NUMERIC,
    similarity_score        NUMERIC,
    composite_ml_score      NUMERIC,
    shap_reason             TEXT,
    extra                   JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_actions (
    id              BIGSERIAL PRIMARY KEY,
    work_id         TEXT NOT NULL REFERENCES works(work_id) ON DELETE CASCADE,
    action          TEXT NOT NULL CHECK (action IN ('cleared','escalated','confirmed')),
    note            TEXT,
    reviewer        TEXT,
    risk_score_at   NUMERIC,
    risk_tier_at    TEXT,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_works_tier       ON works(risk_tier);
CREATE INDEX IF NOT EXISTS idx_works_state      ON works(state);
CREATE INDEX IF NOT EXISTS idx_works_ida        ON works(ida);
CREATE INDEX IF NOT EXISTS idx_works_similarity ON works(similarity_score) WHERE similarity_score > 0;
CREATE INDEX IF NOT EXISTS idx_audit_workid     ON audit_actions(work_id);

CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    role          TEXT NOT NULL CHECK (role IN ('ministry','state_nodal','district_authority','mp','auditor')),
    scope         JSONB NOT NULL DEFAULT '{}'::jsonb,
    salt          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def get_conn():
    return engine.connect()


def init_schema(conn) -> None:
    for stmt in (s.strip() for s in SCHEMA.split(';')):
        if stmt:
            conn.execute(text(stmt))
    conn.commit()


def upsert_user(conn, username, role, scope, salt, password_hash, display_name=None) -> None:
    conn.execute(
        text("""
            INSERT INTO users (username, role, scope, salt, password_hash, display_name)
            VALUES (:username, :role, CAST(:scope AS jsonb), :salt, :password_hash, :display_name)
            ON CONFLICT (username) DO UPDATE SET
                role = EXCLUDED.role,
                scope = EXCLUDED.scope,
                salt = EXCLUDED.salt,
                password_hash = EXCLUDED.password_hash,
                display_name = EXCLUDED.display_name
        """),
        {'username': username, 'role': role, 'scope': json.dumps(scope or {}), 'salt': salt,
         'password_hash': password_hash, 'display_name': display_name},
    )
    conn.commit()


def get_user(conn, username) -> Optional[dict]:
    row = conn.execute(
        text('SELECT username, role, scope, salt, password_hash, display_name FROM users WHERE username = :u'),
        {'u': username},
    ).mappings().first()
    return dict(row) if row else None


def _pyval(v):
    """Convert a pandas/numpy scalar to a plain Python value; NaN -> None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if pd.isna(f) else f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (dict, list)):
        return json.dumps(v, default=str)
    return v


def _row_dict(row):
    """Rows from `.mappings()` iteration are already RowMapping -> dict."""
    return dict(row)


def upsert_works(conn, df: pd.DataFrame) -> int:
    """Upsert the scored frame into `works`. Returns rows written.

    Bulk path uses psycopg2's `execute_batch` on the underlying DBAPI session
    (SQLAlchemy connection-managed) — same batching win as the pre-SQLAlchemy
    implementation; generic SQLAlchemy `executemany` loops row-by-row and is
    ~20x slower at 48,924 rows.
    """
    cols = [c for c in EXPLICIT_COLS if c in df.columns]
    records = []
    skipped = 0
    for _, r in df.iterrows():
        wid = r.get('work_id')
        if wid is None or (isinstance(wid, float) and pd.isna(wid)):
            skipped += 1  # unaddressable rows: no extracted work_id (Module 1)
            continue
        explicit = tuple(
            bool(r.get(c)) if c == 'bypass_ml' else _pyval(r.get(c))
            for c in cols
        )
        extra = json.dumps(
            {c: _pyval(r.get(c)) for c in r.index if c not in cols},
            default=str)
        records.append(explicit + (extra,))

    placeholders = ', '.join(['%s'] * (len(cols) + 1))
    upsert = f"""
        INSERT INTO works ({', '.join(cols)}, extra)
        VALUES ({placeholders})
        ON CONFLICT (work_id) DO UPDATE SET
            {', '.join(f'{c} = EXCLUDED.{c}' for c in cols)},
            extra = EXCLUDED.extra,
            ingested_at = now()
    """
    raw = conn.connection  # underlying psycopg2 connection (SQLAlchemy-managed)
    with raw.cursor() as cur:
        psycopg2.extras.execute_batch(cur, upsert, records, page_size=2000)
    conn.commit()
    if skipped:
        print(f'[db] skipped {skipped} unaddressable row(s) (no work_id)')
    return len(records)


def get_work(conn, work_id: str) -> Optional[Dict]:
    row = conn.execute(text('SELECT * FROM works WHERE work_id = :wid'),
                       {'wid': work_id}).mappings().first()
    if row is None:
        return None
    row = dict(row)
    row['extra'] = json.loads(row['extra']) if isinstance(row.get('extra'), str) else (row.get('extra') or {})
    if not isinstance(row['extra'], dict):
        row['extra'] = {}
    return row


def query_alerts(conn, tier: Optional[str] = None, state: Optional[str] = None,
                 ida: Optional[str] = None, mp: Optional[str] = None,
                 limit: int = 50) -> List[Dict]:
    sql = ('SELECT work_id, risk_score, risk_tier, state, ida, mp_name, '
           'work_description, sanction_amount, shap_reason FROM works WHERE 1=1')
    args: Dict[str, object] = {}
    if tier:
        sql += ' AND risk_tier = :tier'
        args['tier'] = tier
    if state:
        sql += ' AND LOWER(state) LIKE :state'
        args['state'] = f'%{state.lower()}%'
    if ida:
        sql += ' AND LOWER(ida) LIKE :ida'
        args['ida'] = f'%{ida.lower()}%'
    if mp:
        sql += ' AND LOWER(mp_name) LIKE :mp'
        args['mp'] = f'%{mp.lower()}%'
    sql += f' ORDER BY risk_score DESC, work_id LIMIT {int(limit)}'
    return [_row_dict(r) for r in conn.execute(text(sql), args).mappings()]


def record_action(conn, work_id: str, action: str, note: Optional[str],
                  reviewer: Optional[str], risk_score=None, risk_tier=None) -> None:
    conn.execute(text("""
        INSERT INTO audit_actions (work_id, action, note, reviewer, risk_score_at, risk_tier_at)
        VALUES (:wid, :action, :note, :reviewer, :score, :tier)
    """), {'wid': work_id, 'action': action, 'note': note,
           'reviewer': reviewer, 'score': risk_score, 'tier': risk_tier})
    conn.commit()


def delete_actions(conn, work_id: str) -> int:
    """Test/ops helper — remove all decisions for a work; returns deleted count."""
    res = conn.execute(text('DELETE FROM audit_actions WHERE work_id = :wid'),
                       {'wid': work_id})
    conn.commit()
    return res.rowcount


def get_actions(conn, work_id: Optional[str] = None) -> List[Dict]:
    sql = 'SELECT * FROM audit_actions'
    args: Dict[str, object] = {}
    if work_id:
        sql += ' WHERE work_id = :wid'
        args['wid'] = work_id
    sql += ' ORDER BY recorded_at'
    return [_row_dict(r) for r in conn.execute(text(sql), args).mappings()]


def get_action_feed(conn, limit: int = 200) -> List[Dict]:
    """Auditor view: every decision joined with its work's human context."""
    sql = """
        SELECT a.id, a.work_id, a.action, a.note, a.reviewer,
               a.risk_score_at, a.risk_tier_at, a.recorded_at,
               w.work_description, w.state, w.ida, w.mp_name, w.sanction_amount
        FROM audit_actions a
        LEFT JOIN works w ON w.work_id = a.work_id
        ORDER BY a.recorded_at DESC
        LIMIT :lim
    """
    return [_row_dict(r) for r in conn.execute(text(sql), {'lim': int(limit)}).mappings()]


def action_counts(conn) -> Dict[str, int]:
    rows = conn.execute(
        text('SELECT action, COUNT(*) AS n FROM audit_actions GROUP BY action')).mappings()
    by_action = {r['action']: int(r['n']) for r in rows}
    return {
        'total': sum(by_action.values()),
        'cleared': by_action.get('cleared', 0),
        'escalated': by_action.get('escalated', 0),
        'confirmed': by_action.get('confirmed', 0),
    }


def table_schema(conn) -> Dict[str, List[dict]]:
    """information_schema -> {table: [columns with types]}."""
    rows = conn.execute(text("""
        SELECT table_name, ordinal_position, column_name, data_type,
               is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)).mappings()
    out: Dict[str, List[dict]] = {}
    for r in rows:
        out.setdefault(r['table_name'], []).append({
            'column': r['column_name'], 'type': r['data_type'],
            'nullable': r['is_nullable'], 'default': r['column_default'],
        })
    return out


def counts(conn) -> Dict[str, int]:
    works = conn.execute(text('SELECT COUNT(*) FROM works')).scalar()
    actions = conn.execute(text('SELECT COUNT(*) FROM audit_actions')).scalar()
    return {'works': works, 'audit_actions': actions}


def show_schema(conn) -> None:
    schemas = table_schema(conn)
    print('\n=== POSTGRES SCHEMA (public) ===')
    for table, cols in schemas.items():
        print(f'\nTABLE {table}')
        for c in cols:
            default = f"  default={c['default']}" if c['default'] else ''
            print(f"  {c['column']:<24} {c['type']:<14} nullable={c['nullable']}{default}")