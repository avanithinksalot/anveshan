"""
Module 4: Isolation Forest (unsupervised anomaly scoring)

Per spec, the composite Risk Score is 40% XGBoost + 40% Isolation Forest +
20% vendor/duplicate signals when no hard rule hit. This module produces the
Isolation Forest half: a 0-1 normalised anomaly score per work.

Signals the spec asks the unsupervised layer to capture: cost anomalies,
timeline anomalies, and vendor concentration. Feature matrix (18 features):

  Cost        sanction_amount, recommended_amount, amount_disbursed,
              total_expenditure, expenditure_vs_recommended_ratio,
              expenditure_vs_disbursed_ratio, disbursed_overrun_flag,
              sanction_vs_recommended_diff_pct, amount_zscore_in_category
  Timeline    days_sanctioned_to_completion, work_status_stage_duration,
              is_overdue_1yr_rule
  Vendor      max_vendor_concentration_score, max_vendor_ida_count,
              max_vendor_mp_count, max_vendor_is_individual_flag
  Integrity   duplicate_work_id_flag, image_missing_flag

Design notes / caveats:
  - Median imputation for missing feature values (IsolationForest can't take
    NaN). Each work's `if_coverage` (fraction of features that were REAL, not
    imputed) is recorded; Module 7 may discount low-coverage scores.
  - contamination=0.05 hyper-parameter prior (only affects predict boundary;
    score_samples is contamination-free) aligned with the ~5.6% hard-hit prior.
  - Score = -score_samples min-max normalised to [0,1]; higher = more anomalous.
  - Computed for ALL works; Module 7 bypasses it where any_hard_violation=1.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict

from sklearn.ensemble import IsolationForest

from src.rule_engine import run_module3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

IF_FEATURES = [
    'sanction_amount', 'recommended_amount', 'amount_disbursed', 'total_expenditure',
    'expenditure_vs_recommended_ratio', 'expenditure_vs_disbursed_ratio',
    'disbursed_overrun_flag', 'sanction_vs_recommended_diff_pct',
    'amount_zscore_in_category', 'days_sanctioned_to_completion',
    'work_status_stage_duration', 'is_overdue_1yr_rule',
    'max_vendor_concentration_score', 'max_vendor_ida_count', 'max_vendor_mp_count',
    'max_vendor_is_individual_flag', 'duplicate_work_id_flag', 'image_missing_flag',
]

CONTAMINATION = 0.05
N_ESTIMATORS = 200
RANDOM_STATE = 42


def _attach_vendor_features(work: pd.DataFrame, vendor_level: pd.DataFrame) -> pd.DataFrame:
    """Map each work's vendor list onto vendor-level features (max per work)."""
    df = work.copy()
    vcols = ['vendor_name', 'vendor_concentration_score', 'vendor_ida_count',
             'vendor_mp_count', 'vendor_is_individual_flag']
    vcols = [c for c in vcols if c in vendor_level.columns]
    vendor_level = vendor_level[vcols].copy()
    vendor_level['vendor_name'] = vendor_level['vendor_name'].astype(str).str.strip().str.upper()

    rows = []
    for idx, vendors in df['vendors'].items():
        agg = {}
        if isinstance(vendors, list) and len(vendors) > 0:
            names = [str(v).strip().upper() for v in vendors]
            sub = vendor_level[vendor_level['vendor_name'].isin(names)]
            for c in ['vendor_concentration_score', 'vendor_ida_count',
                      'vendor_mp_count', 'vendor_is_individual_flag']:
                if c in sub.columns and len(sub) > 0:
                    agg[c] = pd.to_numeric(sub[c], errors='coerce').max()
        rows.append(agg)
    vend = pd.DataFrame(rows, index=df.index)
    for c in ['max_vendor_concentration_score', 'max_vendor_ida_count',
              'max_vendor_mp_count', 'max_vendor_is_individual_flag']:
        base = c.replace('max_', '')
        if base in vend.columns:
            df[c] = vend[base]
        else:
            df[c] = np.nan
    return df


def run_module4(work_level: pd.DataFrame = None, vendor_level: pd.DataFrame = None) -> Dict:
    """Fit IsolationForest, score every work, return scores + model + summary."""
    logger.info("=" * 60)
    logger.info("MODULE 4: Isolation Forest (unsupervised anomaly scoring)")
    logger.info("=" * 60)

    if work_level is None:
        from src.feature_engineering import run_module2
        features = run_module2()
        work_level = features['work_level']
        vendor_level = vendor_level if vendor_level is not None else features['vendor_level']
    if vendor_level is None:
        from src.feature_engineering import run_module2
        logger.info("vendor_level not provided; computing from Module 2")
        vendor_level = run_module2()['vendor_level']

    df = _attach_vendor_features(work_level, vendor_level)

    feats = [c for c in IF_FEATURES if c in df.columns]
    logger.info(f"Isolation Forest features ({len(feats)}): {feats}")

    X_raw = df[feats].apply(pd.to_numeric, errors='coerce')

    # Coverage = fraction of features with a REAL value (not imputed).
    coverage = X_raw.notna().mean(axis=1)

    medians = X_raw.median()
    X = X_raw.fillna(medians)
    X = X.replace([np.inf, -np.inf], np.nan).fillna(medians)

    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
    )
    model.fit(X)

    # score_samples: more negative = more anomalous. Invert + min-max -> [0,1].
    raw = -model.score_samples(X)
    lo, hi = raw.min(), raw.max()
    anomaly = np.where(hi > lo, (raw - lo) / (hi - lo), 0.0)
    predicted = model.predict(X)  # -1 = outlier

    df['if_anomaly_score'] = anomaly
    df['if_predicted_outlier'] = (predicted == -1).astype(int)
    df['if_coverage'] = coverage
    df['if_n_features'] = len(feats)

    summary = {
        'works_scored': int(len(df)),
        'if_predicted_outliers': int((predicted == -1).sum()),
        'median_score': float(np.median(anomaly)),
        'p90_score': float(np.percentile(anomaly, 90)),
        'p99_score': float(np.percentile(anomaly, 99)),
        'mean_coverage': float(coverage.mean()),
        'features_used': feats,
    }
    logger.info(f"\n=== ISOLATION FOREST SUMMARY ===")
    for k, v in summary.items():
        if k == 'features_used':
            continue
        logger.info(f"  {k}: {v}")

    return {'results': df, 'model': model, 'features': feats, 'summary': summary}


if __name__ == "__main__":
    out = run_module4()
    df = out['results']
    feats = out['features']
    summary = out['summary']

    print("\n" + "=" * 80)
    print("MODULE 4 TEST RESULTS — Isolation Forest (unsupervised)")
    print("=" * 80)

    print(f"\nWorks scored: {summary['works_scored']}")
    print(f"Predicted outliers (contamination prior {CONTAMINATION}): {summary['if_predicted_outliers']}")

    print("\n--- Distribution of if_anomaly_score [0,1] ---")
    print(df['if_anomaly_score'].describe().to_string())
    print("\nPercentiles (5, 25, 50, 75, 95, 99):")
    print(df['if_anomaly_score'].quantile([0.05, 0.25, 0.50, 0.75, 0.95, 0.99]).to_string())

    print("\n--- Score bins ---")
    bins = pd.cut(df['if_anomaly_score'], bins=[-0.001, 0.2, 0.4, 0.6, 0.8, 1.001],
                  labels=['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0'])
    print(bins.value_counts().sort_index().to_frame('count'))

    top_cols = (['work_id', 'source_table', 'work_category_suffix', 'work_description',
                 'if_anomaly_score', 'if_predicted_outlier', 'if_coverage']
                + [c for c in feats if c in df.columns])
    top_k = [c for c in top_cols if c in df.columns]

    print("\n--- TOP 10 highest anomaly-scored works (with driving feature values) ---")
    top = df.nlargest(10, 'if_anomaly_score')
    show_cols = ['work_id', 'source_table', 'work_category_suffix', 'work_description',
                 'sanction_amount', 'recommended_amount', 'total_expenditure',
                 'expenditure_vs_disbursed_ratio', 'expenditure_vs_recommended_ratio',
                 'days_sanctioned_to_completion', 'work_status_stage_duration',
                 'max_vendor_concentration_score', 'max_vendor_ida_count', 'max_vendor_mp_count',
                 'if_anomaly_score', 'if_predicted_outlier', 'if_coverage']
    show_cols = [c for c in show_cols if c in top.columns]
    print(top[show_cols].to_string(max_colwidth=40))

    print("\n--- BOTTOM 5 lowest anomaly-scored works (boring / expected-normal) ---")
    bot = df.nsmallest(5, 'if_anomaly_score')
    print(bot[show_cols].to_string(max_colwidth=40))

    # ---- SANITY: clearly-compliant works should score LOW ----
    print("\n--- SANITY CHECK: clearly-compliant known-good works should score LOW ---")
    clean_sample = [
        'WS/MP620/2024-2025/133166',
        'WS/MP418/2024-2025/133409',
        'WS/MP577/2025-2026/133549',
        'WS/MP577/2025-2026/133551',
        'WS/MP577/2025-2026/133563',
    ]
    check = df[df['work_id'].isin(clean_sample)][['work_id', 'if_anomaly_score',
                                                  'if_predicted_outlier', 'if_coverage']]
    print(check.to_string(index=False))
    max_clean = check['if_anomaly_score'].max()
    print(f"\nMax anomaly score among compliant works: {max_clean:.3f} "
          f"(median overall: {summary['median_score']:.3f})")
    if max_clean <= 0.5:
        print("PASS ✓ compliant works sit below the median-ish anomaly band")
    else:
        print("WARN — a clearly-compliant work scored high; investigate drivers above")