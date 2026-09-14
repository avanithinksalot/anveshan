"""
Module 7: Composite Risk Score + tiers

Implements the spec formula EXACTLY:

    IF hard_rule_violation:  score = 80-100  (deterministic severity; BYPASSES ML)
    ELSE:                    score =  0.40 * isolation_forest_normalized
                                   + 0.40 * xgboost_risk_probability
                                   + 0.20 * avg(vendor_concentration_score,
                                                 similarity_score)

Tiers:  Low 0-39 | Medium 40-69 | High 70-100.

Hard-rule severity (deterministic, non-ML):
    80 + 20 * max_severity  where each rule contributes a 0-1 severity:
      - completed_overdue  min(1, overdue_days / 730)
      - disallowed_category fixed 0.9
      - allocation_ceiling min(1, violation_amount / allocated_amount)
    ensures hard hits land in the 80-100 band without ML influence.

Notes:
  - bypass_ml is set =1 so downstream consumers (API, DB, UI) can prove the ML
    branch is skipped for these works.
  - similarity_score is a PLACEHOLDER 0.0 until Module 8 (text + image
    similarity) populates it; the formula is already reading the column, so the
    wiring is done.
  - vendor_concentration_score (max across a work's vendors) is median-imputed
    when missing (no expenditure row for that work).
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict

from src.shap_explain import run_module6

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HARD_MIN, HARD_MAX = 80, 100
HARD_BYPASS = 1


def _hard_severity(row: pd.Series) -> float:
    """Deterministic 0-1 severity for hard-rule-flagged works."""
    severities = []

    od = row.get('completed_overdue_days')
    if pd.notna(od) and float(od) > 0:
        severities.append(min(1.0, float(od) / 730.0))

    if row.get('rule_disallowed_category', 0) == 1:
        severities.append(0.9)

    alloc = row.get('allocated_amount')
    viol = row.get('allocation_violation_amount')
    if pd.notna(alloc) and pd.notna(viol) and float(alloc) > 0:
        severities.append(min(1.0, float(viol) / float(alloc)))

    if not severities:
        return 0.5  # rule flagged but no severity detail -> mid-band 90
    return float(np.max(severities))


def _compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # vendor concentration median-impute (missing = no expenditure row)
    vc = pd.to_numeric(df['max_vendor_concentration_score'], errors='coerce')
    vc_median = vc.median()
    vc = vc.fillna(vc_median if pd.notna(vc_median) else 0.0)

    # similarity_score: Module 8 will populate; default 0.0 until then
    sim = pd.to_numeric(df['similarity_score'], errors='coerce') if 'similarity_score' in df.columns else pd.Series(0.0, index=df.index)
    sim = sim.fillna(0.0)

    vendor_sim_avg = (vc + sim) / 2.0

    if_score = pd.to_numeric(df['if_anomaly_score'], errors='coerce').fillna(0.0)
    xgb_prob = pd.to_numeric(df['xgb_risk_probability'], errors='coerce').fillna(0.0)

    df['composite_ml_score'] = np.round(
        100.0 * (0.40 * if_score + 0.40 * xgb_prob + 0.20 * vendor_sim_avg), 1
    )
    df['composite_vendor_component'] = np.round(vendor_sim_avg, 4)

    hard = (df['any_hard_violation'] == 1).astype(int)
    df['bypass_ml'] = hard

    severity = df.apply(lambda r: _hard_severity(r) if r['any_hard_violation'] == 1 else np.nan, axis=1)
    df['hard_severity'] = severity

    df['risk_score'] = np.where(
        hard == 1,
        np.round(HARD_MIN + 20 * severity.fillna(0.5), 1),
        df['composite_ml_score'],
    )
    df['risk_tier'] = np.where(
        df['risk_score'] >= 70, 'High',
        np.where(df['risk_score'] >= 40, 'Medium', 'Low'),
    )
    return df


def _score_breakdown(df: pd.DataFrame, n_top: int = 10) -> pd.DataFrame:
    """Feature breakdown rows for the test sample."""
    cols = ['work_id', 'source_table', 'any_hard_violation', 'bypass_ml',
            'if_anomaly_score', 'xgb_risk_probability',
            'composite_vendor_component', 'composite_ml_score',
            'hard_severity', 'risk_score', 'risk_tier', 'shap_reason']
    cols = [c for c in cols if c in df.columns]
    return df[cols]


def run_module7(df: pd.DataFrame = None) -> Dict:
    """Compute composite risk scores + tiers; return scored frame + summary."""
    logger.info("=" * 60)
    logger.info("MODULE 7: Composite Risk Score + tiers")
    logger.info("=" * 60)

    if df is None:
        out6 = run_module6()
        df = out6['results']

    out = _compute_scores(df)

    summary = {
        'works_scored': int(len(out)),
        'n_hard_bypass': int(out['bypass_ml'].sum()),
        'n_low': int((out['risk_tier'] == 'Low').sum()),
        'n_medium': int((out['risk_tier'] == 'Medium').sum()),
        'n_high': int((out['risk_tier'] == 'High').sum()),
    }
    logger.info(f"\n=== COMPOSITE SUMMARY ===")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")

    return {'results': out, 'summary': summary}


if __name__ == "__main__":
    out = run_module7()
    df = out['results']
    summary = out['summary']

    print("\n" + "=" * 80)
    print("MODULE 7 TEST RESULTS — Composite Risk Score + tiers")
    print("=" * 80)

    print(f"\nTotal works scored: {summary['works_scored']}")
    print(f"Hard-rule bypassed (score forced 80-100): {summary['n_hard_bypass']}")
    print(f"Tiers: Low={summary['n_low']}  Medium={summary['n_medium']}  High={summary['n_high']}")

    print("\n--- Score distribution ---")
    print(df['risk_score'].describe().to_string())

    print("\n--- Full score breakdown: sample across Low / Medium / High ---")
    # pick 4 Low, 3 Medium, 3 High deterministically by score rank
    low = df[df['risk_tier'] == 'Low'].nsmallest(4, 'risk_score')
    med = df[df['risk_tier'] == 'Medium'].nsmallest(3, 'risk_score')
    high = df[df['risk_tier'] == 'High'].nlargest(3, 'risk_score')
    sample = pd.concat([low, med, high])
    cols = ['work_id', 'source_table', 'any_hard_violation', 'bypass_ml',
            'if_anomaly_score', 'xgb_risk_probability', 'composite_vendor_component',
            'composite_ml_score', 'hard_severity', 'risk_score', 'risk_tier']
    print(_score_breakdown(sample)[cols].to_string(index=False))

    print("\n--- 5 known-compliant works (expect Low, no bypass) ---")
    clean_sample = [
        'WS/MP620/2024-2025/133166',
        'WS/MP418/2024-2025/133409',
        'WS/MP577/2025-2026/133549',
        'WS/MP577/2025-2026/133551',
        'WS/MP577/2025-2026/133563',
    ]
    check = df[df['work_id'].isin(clean_sample)][[
        'work_id', 'if_anomaly_score', 'xgb_risk_probability',
        'composite_vendor_component', 'composite_ml_score', 'risk_score', 'risk_tier', 'bypass_ml']]
    print(check.to_string(index=False))

    print("\n--- 5 hard-rule-flagged works (expect High >= 80, bypass_ml=1) ---")
    hard_df = df[df['any_hard_violation'] == 1].head(5)
    print(hard_df[[
        'work_id', 'rule_completed_overdue', 'rule_disallowed_category',
        'rule_allocation_ceiling', 'hard_severity', 'risk_score', 'risk_tier', 'bypass_ml']].to_string(index=False))

    print("\n--- Verification: bypass_ml contract ---")
    print(f"Hard violations: {df['any_hard_violation'].sum()}")
    print(f"bypass_ml set:   {int(df['bypass_ml'].sum())}")
    print(f"Hard-flagged works with score >= 80: {(df['bypass_ml']==1) & (df['risk_score']>=80)} count "
          f"= {int(((df['bypass_ml']==1) & (df['risk_score']>=80)).sum())}")
    over70 = (df['risk_score'] >= 70) & (df['bypass_ml'] == 1)
    extra = (df['bypass_ml'] == 1) & (df['risk_score'] < 70)
    print(f"False claims of non-bypass (hard but < 70): {int(extra.sum())}")