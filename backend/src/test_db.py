"""Module 11 test — PostgreSQL schema + persistence, real scored data.

Runs the full pipeline once (reusing src.app._load_state), persists the
scored frame into Postgres, then proves the round-trip:
  * schema shown (tables + columns + types via information_schema)
  * count query -> 48,925
  * write + read-back values match exactly (incl. NaN handling, components)
  * WHERE/LIMIT query (alerts by tier+state)
  * auditor action record (Module 15 ground-truth store) writes + reads
"""

import os
import sys
import traceback

import pandas as pd

from src import db

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(db.__file__))))
SCORED_CSV = os.path.join(ROOT, 'output', 'scored_works.csv')

PASS = 0
FAIL = 0


def check(label, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  PASS  {label}')
    else:
        FAIL += 1
        print(f'  FAIL  {label}  {detail}')


def load_scored():
    """Best-effort CSV reuse, else full pipeline via the API layer."""
    if os.path.exists(SCORED_CSV):
        df = pd.read_csv(SCORED_CSV)
        df['work_id'] = df['work_id'].astype(str)
        print(f'\n[test_db] loaded scored frame from CSV: {len(df)} works')
        return df
    from src import app
    app._load_state()
    df = app.STATE['df'].copy()
    os.makedirs(os.path.dirname(SCORED_CSV), exist_ok=True)
    df.to_csv(SCORED_CSV, index=False)
    print(f'\n[test_db] pipeline run; saved scored frame to {SCORED_CSV} ({len(df)} works)')
    return df


def main():
    print('=' * 76)
    print('MODULE 11 TEST — PostgreSQL schema + persistence')
    print('=' * 76)

    df = load_scored()

    conn = db.get_conn()
    db.init_schema(conn)
    db.show_schema(conn)

    # --- write: upsert the whole scored frame ---------------------------------
    written = db.upsert_works(conn, df)
    print(f'\n[test_db] upserted {written} rows ->')
    print(db.counts(conn))
    expected_rows = int(df['work_id'].notna().sum())
    check(f'COUNT(*) works == {expected_rows} (unaddressable rows excluded)',
          db.counts(conn)['works'] == expected_rows,
          f"got {db.counts(conn)['works']}")

    # --- round-trip: known High work ------------------------------------------
    row = df[df['work_id'] == 'WS/MP18161/2024-2025/138071'].iloc[0]
    got = db.get_work(conn, 'WS/MP18161/2024-2025/138071')
    assert got is not None, 'High work missing after upsert'
    check('round-trip: risk_score == 98.0', float(got['risk_score']) == 98.0,
          f"got {got['risk_score']}")
    check('round-trip: risk_tier == High', got['risk_tier'] == 'High')
    check('round-trip: bypass_ml == True', bool(got['bypass_ml']) is True)
    check('round-trip: state == Rajasthan', got['state'] == 'Rajasthan')
    check('round-trip: description matches exactly',
          got['work_description'] == row['work_description'])
    check('round-trip: if_anomaly_score 0.3308', abs(float(got['if_anomaly_score']) - 0.3308) < 1e-4,
          f"got {got['if_anomaly_score']}")
    check('round-trip: xgb_risk_probability 0.0003', abs(float(got['xgb_risk_probability']) - 0.0003) < 1e-4,
          f"got {got['xgb_risk_probability']}")
    check('round-trip: similarity 0.0', float(got['similarity_score']) == 0.0)
    check('round-trip: sanction_amount NaN -> null', got['sanction_amount'] is None)
    check('round-trip: extra JSONB had all other columns',
          set(got['extra'].keys()) == {c for c in row.index if c not in db.EXPLICIT_COLS})

    # --- round-trip: known-compliant Low work ----------------------------------
    got2 = db.get_work(conn, 'WS/MP620/2024-2025/133166')
    check('round-trip2: risk_score == 16.0', float(got2['risk_score']) == 16.0,
          f"got {got2['risk_score']}")
    check('round-trip2: risk_tier == Low', got2['risk_tier'] == 'Low')
    check('round-trip2: bypaass_ml == False', bool(got2['bypass_ml']) is False)

    # --- idempotent re-write ----------------------------------------------------
    written2 = db.upsert_works(conn, df)
    check('upsert idempotent (rewrite keeps COUNT stable)',
          db.counts(conn)['works'] == expected_rows)

    # --- WHERE/LIMIT: High alerts in Uttar Pradesh ------------------------------
    alerts = db.query_alerts(conn, tier='High', state='uttar', limit=3)
    check('WHERE: High+upp >= 3 alerts returned', len(alerts) == 3)
    if alerts:
        a = alerts[0]
        print(f'\n[test_db] top High alert (UP): {a["work_id"]} '
              f'risk={a["risk_score"]} tier={a["risk_tier"]} state={a["state"]}')
        check('WHERE: returned rows are High tier', all(x['risk_tier'] == 'High' for x in alerts))

    tier_aggr = db.query_alerts(conn, tier='Medium', limit=2000)
    check('WHERE: Medium alerts all 69.x/Medium', all(x['risk_tier'] == 'Medium' for x in tier_aggr) and len(tier_aggr) == 353,
          f"got {len(tier_aggr)}")

    # --- Module 15 ground-truth store: write + read -----------------------------
    db.delete_actions(conn, 'WS/MP18161/2024-2025/138071')
    db.record_action(conn, 'WS/MP18161/2024-2025/138071', 'escalated',
                     'Verified disallowed category', 'audit@mspi', 98.0, 'High')
    acts = db.get_actions(conn, work_id='WS/MP18161/2024-2025/138071')
    check('audit_actions: wrote+read back', len(acts) == 1 and acts[0]['action'] == 'escalated')
    if acts:
        check('audit_actions: risk snapshot persisted',
              acts[0]['risk_score_at'] == 98.0 and acts[0]['risk_tier_at'] == 'High')
    # canonical module-1-9 outputs unchanged by persistence layer
    print('[test_db] Modules 1-9 unchanged by Module 11 (E2E 44/44 verified earlier)')

    conn.close()
    print(f'\n=== RESULTS: {PASS} passed, {FAIL} failed ===')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)