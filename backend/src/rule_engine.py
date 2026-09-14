"""
Module 3: Deterministic Rule Engine (hard violations)

Implements the MPLADS hard rules from the spec. ANY hard violation forces
the composite Risk Score to 80-100 by BYPASSING the ML pipeline in code
(contract consumed by Module 7, not just the score formula).

Rules:
  R1  1-year completion window (split by verifiability)
       - rule_completed_overdue (HARD, verified): completed works where
         (completion_date - sanction_date) > 365 days. Verified breach of
         the 1-year window on a completed work.
       - rule_pipeline_stale (SOFT, not a bypass): works still in the
         pipeline (no completion; status not terminal) >365 days after
         sanction. MPLADS allows sanctioned extensions, which this export
         cannot distinguish, so this is a review signal, not a hard hit.
  R2  disallowed work categories (HARD): context-aware flag from Module 2
      (only when the restricted object is the constructed item, not a
      landmark, and the category suffix does not sanction the domain).
  R3  allocation ceiling (HARD when assessable): work sanction amount >
      MP annual allocated amount.
      NOTE: the MP <-> allocated-limit join covers effectively ~0 works on
      this export (normalised MP-name overlap = 1 MP), so R3 renders as not
      assessable here but is implemented for enriched data.
  R4  SC/ST quota compliance — NOT ENFORCEABLE AS A HARD RULE on this
      export. There is no per-work SC/ST beneficiary-designation field.
      The "(SC)"/"(ST)" markers are seat metadata: all 78 SC-seat and all
      41 ST-seat MPs run 100% consistent (0 violations), while general-seat
      MPs would be mass-flagged without evidence of an actual deficit.
      Exposed as INFORMATIONAL per-MP shares only (may be surfaced to
      Ministry but never bypasses ML).

Outputs:
  work_rules (per work, incl. any_hard_violation + bypass_ml)
  mp_rules   (per normalised MP: informational SC/ST + allocation stats)
  summary    (counts per rule)
"""

import re
import logging
import pandas as pd
import numpy as np
from typing import Dict

from src.feature_engineering import run_module2, norm_mp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MPLADS_COMPLETION_DAYS = 365
MPLADS_EXTENSION_DAYS = 730  # for transparency reporting only
SC_MARKER = re.compile(r'\(\s*SC\s*\)', re.IGNORECASE)
ST_MARKER = re.compile(r'\(\s*ST\s*\)', re.IGNORECASE)
TERMINAL_STATUSES = {'work completed'}


def _today():
    return pd.Timestamp.now()


def _compute_work_rules(work: pd.DataFrame) -> pd.DataFrame:
    """Apply R1 (hard + soft), R2, R3 at work level."""
    df = work.copy()
    today = _today()

    sanction = pd.to_datetime(df['sanction_date'], errors='coerce')
    completion = pd.to_datetime(df['completion_date'], errors='coerce')
    status = df['work_status'].fillna('').astype(str).str.lower().str.strip()

    completed_days = (completion - sanction).dt.days
    pipeline_days = (today - sanction).dt.days

    # --- R1 hard: verified breach of the 1-year window on completed works ---
    df['rule_completed_overdue'] = (
        (completed_days > MPLADS_COMPLETION_DAYS)
    ).astype(int)
    df.loc[completion.isna(), 'rule_completed_overdue'] = np.nan
    df['completed_overdue_days'] = np.where(
        completed_days.notna(),
        np.maximum(completed_days - MPLADS_COMPLETION_DAYS, 0),
        np.nan,
    )
    df['completed_overdue_2yr'] = (
        (completed_days > MPLADS_EXTENSION_DAYS)
    ).astype(int)
    df.loc[completion.isna(), 'completed_overdue_2yr'] = np.nan

    # --- R1 soft: still in pipeline >365 days after sanction ---
    df['rule_pipeline_stale'] = (
        (completion.isna())
        & (sanction.notna())
        & (~status.isin(TERMINAL_STATUSES))
        & (pipeline_days > MPLADS_COMPLETION_DAYS)
    ).astype(int)
    df.loc[completion.notna() | sanction.isna(), 'rule_pipeline_stale'] = np.nan
    df['pipeline_stale_days'] = np.where(
        (completion.isna()) & (sanction.notna()),
        np.maximum(pipeline_days - MPLADS_COMPLETION_DAYS, 0),
        np.nan,
    )

    # --- R2: disallowed work category ---
    df['rule_disallowed_category'] = df['disallowed_category_keyword_flag'].fillna(0).astype(int)

    # --- R3: work-level allocation ceiling ---
    sanction_amt = pd.to_numeric(df['sanction_amount'], errors='coerce')
    alloc_amt = pd.to_numeric(df['allocated_amount'], errors='coerce')
    df['rule_allocation_ceiling'] = (
        (sanction_amt > alloc_amt) & (alloc_amt.notna())
    ).astype(int)
    df['allocation_violation_amount'] = np.where(
        (sanction_amt > alloc_amt) & (alloc_amt.notna()),
        sanction_amt - alloc_amt,
        np.nan,
    )

    # --- any hard violation + ML bypass contract ---
    violation_cols = ['rule_completed_overdue', 'rule_disallowed_category', 'rule_allocation_ceiling']
    df['any_hard_violation'] = (
        df[violation_cols].fillna(0).astype(int).max(axis=1)
    ).astype(int)
    df['bypass_ml'] = df['any_hard_violation']

    keep = [
        'work_id', 'source_table', 'mp_name', 'constituency', 'ida', 'state',
        'work_category', 'work_category_suffix', 'work_status', 'sanction_date',
        'completion_date', 'sanction_amount', 'allocated_amount',
        'rule_completed_overdue', 'completed_overdue_days', 'completed_overdue_2yr',
        'rule_pipeline_stale', 'pipeline_stale_days',
        'rule_disallowed_category', 'disallowed_keyword_match',
        'rule_allocation_ceiling', 'allocation_violation_amount',
        'any_hard_violation', 'bypass_ml',
    ]
    return df[[c for c in keep if c in df.columns]]


def _compute_mp_rules(work: pd.DataFrame) -> pd.DataFrame:
    """MP-level informational view + R3 aggregate + R4 (informational only)."""
    df = work.copy()
    df['mp_norm'] = df['mp_name'].apply(norm_mp)

    def _res_flags(row):
        sc = st = 0
        tagged = 0
        for c in ['ida', 'constituency']:
            v = row.get(c)
            if pd.isna(v):
                continue
            s = str(v)
            if SC_MARKER.search(s):
                sc = 1
            if ST_MARKER.search(s):
                st = 1
        d = row.get('work_description')
        if pd.notna(d):
            dl = str(d).lower()
            if re.search(r's\.?\s*c\.?\s*work|s\.?c\.? work|\(s\.c\.\)', dl) or '(sc)' in dl:
                tagged = 1
            if re.search(r's\.?\s*t\.?\s*work|s\.?t\.? work|\(s\.t\.\)', dl) or '(st)' in dl:
                tagged = 1
        return pd.Series({'seat_sc': sc, 'seat_st': st, 'desc_scst_tag': tagged})

    flags = df.apply(_res_flags, axis=1)
    df['seat_sc'] = flags['seat_sc']
    df['seat_st'] = flags['seat_st']
    df['desc_scst_tag'] = flags['desc_scst_tag']

    g = df.groupby('mp_norm').agg(
        mp_total_works=('work_id', 'size'),
        mp_seat_sc_works=('seat_sc', 'sum'),
        mp_seat_st_works=('seat_st', 'sum'),
        mp_desc_scst_works=('desc_scst_tag', 'sum'),
        mp_total_sanctioned=('sanction_amount', lambda s: pd.to_numeric(s, errors='coerce').sum()),
    ).reset_index()

    g['mp_seat_sc_share'] = np.where(g['mp_total_works'] > 0, g['mp_seat_sc_works'] / g['mp_total_works'], np.nan)
    g['mp_seat_st_share'] = np.where(g['mp_total_works'] > 0, g['mp_seat_st_works'] / g['mp_total_works'], np.nan)
    g['mp_desc_scst_share'] = np.where(g['mp_total_works'] > 0, g['mp_desc_scst_works'] / g['mp_total_works'], np.nan)

    # R4 is informational: no hard flag column. Rationale documented in module docstring.
    g['sc_st_quota_assessable'] = 0  # 0 = not assessable from this export

    mp_alloc = (
        df[['mp_norm', 'allocated_amount']]
        .dropna(subset=['allocated_amount'])
        .drop_duplicates('mp_norm')
    )
    g = g.merge(mp_alloc, on='mp_norm', how='left')
    g['rule_allocation_ceiling_mp'] = (
        (g['mp_total_sanctioned'] > g['allocated_amount']) & (g['allocated_amount'].notna())
    ).astype(int)

    return g


def run_module3(features: Dict[str, pd.DataFrame] = None) -> Dict:
    """Run the deterministic rule engine and return work_rules / mp_rules / summary."""
    logger.info("=" * 60)
    logger.info("MODULE 3: Deterministic Rule Engine")
    logger.info("=" * 60)

    if features is None:
        features = run_module2()

    work = features['work_level']
    work_rules = _compute_work_rules(work)
    mp_rules = _compute_mp_rules(work)

    summary = {
        'rule_completed_overdue': int((work_rules['rule_completed_overdue'] == 1).sum()),
        'completed_overdue_2yr': int((work_rules['completed_overdue_2yr'] == 1).sum()),
        'rule_pipeline_stale': int((work_rules['rule_pipeline_stale'] == 1).sum()),
        'rule_disallowed_category': int(work_rules['rule_disallowed_category'].sum()),
        'rule_allocation_ceiling': int(work_rules['rule_allocation_ceiling'].sum()),
        'any_hard_violation': int(work_rules['any_hard_violation'].sum()),
        'mp_allocation_ceiling_violations': int(mp_rules['rule_allocation_ceiling_mp'].sum()),
        'sc_st_quota_assessable_mp': int(mp_rules['sc_st_quota_assessable'].sum()),
    }

    logger.info(f"\n=== RULE SUMMARY ===")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")
    logger.info(f"Work rules shape: {work_rules.shape}")
    logger.info(f"MP rules shape: {mp_rules.shape}")

    return {'work_rules': work_rules, 'mp_rules': mp_rules, 'summary': summary}


if __name__ == "__main__":
    results = run_module3()

    work_rules = results['work_rules']
    mp_rules = results['mp_rules']
    summary = results['summary']

    print("\n" + "=" * 80)
    print("MODULE 3 TEST RESULTS — Rule Engine (deterministic)")
    print("=" * 80)

    print(f"\nWork rules shape: {work_rules.shape}")
    print(f"Rule summary: {summary}")
    print(f"\nTotal works with ANY hard violation: {summary['any_hard_violation']} / {len(work_rules)}"
          f" ({100.0 * summary['any_hard_violation'] / len(work_rules):.1f}%)")

    def show_samples(df, mask, cols, n=5, title=""):
        sub = df[mask]
        print(f"\n### {title} — {len(sub)} rows ###")
        if len(sub) == 0:
            print("(none)")
            return
        cols = [c for c in cols if c in sub.columns]
        print(sub[cols].head(n).to_string())

    show_samples(work_rules, work_rules['rule_completed_overdue'] == 1,
                 ['work_id', 'work_status', 'sanction_date', 'completion_date',
                  'completed_overdue_days', 'completed_overdue_2yr', 'rule_completed_overdue'],
                 5, "R1-HARD — completed works that breached the 1-year window")

    show_samples(work_rules, work_rules['rule_pipeline_stale'] == 1,
                 ['work_id', 'work_status', 'sanction_date', 'pipeline_stale_days', 'rule_pipeline_stale'],
                 5, "R1-SOFT — works still in pipeline >365 days after sanction (no ML bypass)")

    show_samples(work_rules, work_rules['rule_disallowed_category'] == 1,
                 ['work_id', 'work_category_suffix', 'work_description',
                  'disallowed_keyword_match', 'rule_disallowed_category'],
                 5, "R2-HARD — disallowed work category (context-aware)")

    show_samples(work_rules, work_rules['rule_allocation_ceiling'] == 1,
                 ['work_id', 'work_category_suffix', 'sanction_amount', 'allocated_amount',
                  'allocation_violation_amount', 'rule_allocation_ceiling'],
                 5, "R3-HARD — sanction amount exceeds MP allocated ceiling")

    print("\n### R4 — SC/ST quota: informational view ###")
    print(f"MPs assessable for a hard SC/ST rule on this export: {summary['sc_st_quota_assessable_mp']}"
          " (0 = NOT assessable — no beneficiary-designation field)")
    print(f"MPs with any SC/ST benefit tag discoverable in descriptions: "
          f"{int((mp_rules['mp_desc_scst_works'] > 0).sum())} / {len(mp_rules)}")
    print(mp_rules[['mp_norm', 'mp_total_works', 'mp_seat_sc_share', 'mp_seat_st_share',
                    'mp_desc_scst_share', 'sc_st_quota_assessable']].head(5).to_string())

    print("\n### MP-level allocation ceiling (R3 aggregate) ###")
    mp_alloc_viol = mp_rules[mp_rules['rule_allocation_ceiling_mp'] == 1]
    print(f"Violations: {len(mp_alloc_viol)} (allocated-limit join coverage effectively 0 on this export)")
    if len(mp_alloc_viol):
        print(mp_alloc_viol[['mp_norm', 'mp_total_sanctioned', 'allocated_amount']].to_string())

    # ---- ZERO-FALSE-TRIGGER verification on clearly-compliant works ----
    print("\n" + "=" * 80)
    print("ZERO FALSE-TRIGGER CHECK — clearly-compliant known-good works")
    print("=" * 80)
    clean_sample = [
        'WS/MP620/2024-2025/133166',
        'WS/MP418/2024-2025/133409',
        'WS/MP577/2025-2026/133549',
        'WS/MP577/2025-2026/133551',
        'WS/MP577/2025-2026/133563',
    ]
    check = work_rules[work_rules['work_id'].isin(clean_sample)].copy()
    print(check[['work_id', 'sanction_date', 'completion_date', 'rule_completed_overdue',
                 'rule_pipeline_stale', 'rule_disallowed_category', 'rule_allocation_ceiling',
                 'any_hard_violation']].to_string())
    false_hits = check['any_hard_violation'].sum()
    print(f"\nFalse triggers on clearly-compliant works: {int(false_hits)} (expected 0)")
    print("PASS ✓" if false_hits == 0 else "FAIL — investigate")