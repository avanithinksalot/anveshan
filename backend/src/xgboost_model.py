"""
Module 5: XGBoost + SMOTE (supervised risk scoring)

Per spec, XGBoost outputs a calibrated 0-1 risk probability contributing
40% of the composite Risk Score (Module 7).

Training labels (derived, since no real CAG-report ground truth exists in
this export):
  1 = any_hard_violation == 1  (Module 3 rule breaches: 2,749 works, ~5.6%)
  1 = if_predicted_outlier == 1 AND anomaly_score > 0.6  (Module 4 top IF hits)
  0 = everything else

SMOTE up-samples the minority (positive) class to 50/50 before training.
80/20 stratified split; metrics reported on the held-out 20%.

Caveat: these are derived labels, not verified fraud. The supervised model
learns a risk surface that reinforces the unsupervised + rule layers.
It will be retrained when real auditor feedback arrives (Module 15).
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, precision_recall_fscore_support,
    roc_auc_score, confusion_matrix,
)
from xgboost import XGBClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

from src.isolation_forest import run_module4
from src.rule_engine import run_module3

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Features fed to XGBoost (superset of IF features, plus rule-derived signals)
XGB_FEATURES = [
    # cost
    'sanction_amount', 'recommended_amount', 'amount_disbursed', 'total_expenditure',
    'expenditure_vs_recommended_ratio', 'expenditure_vs_disbursed_ratio',
    'disbursed_overrun_flag', 'sanction_vs_recommended_diff_pct',
    'amount_zscore_in_category',
    # timeline
    'days_sanctioned_to_completion', 'work_status_stage_duration',
    'is_overdue_1yr_rule',
    # vendor (max across work's vendors)
    'max_vendor_concentration_score', 'max_vendor_ida_count',
    'max_vendor_mp_count', 'max_vendor_is_individual_flag',
    # integrity
    'duplicate_work_id_flag', 'image_missing_flag',
    # IF anomaly score (Module 4 output as feature)
    'if_anomaly_score',
]

RANDOM_STATE = 42
TEST_SIZE = 0.2
SMOTE_K_NEIGHBORS = 5


def _derive_labels(df: pd.DataFrame) -> pd.Series:
    """Create binary labels from rule violations + IF top outliers."""
    rule_hit = (df['any_hard_violation'] == 1).astype(int)
    if_top = (
        (df.get('if_predicted_outlier', 0) == 1)
        & (df.get('if_anomaly_score', 0) > 0.6)
    ).astype(int)
    label = ((rule_hit == 1) | (if_top == 1)).astype(int)
    logger.info(f"Derived labels: {label.sum()} positive / {(1-label).sum()} negative "
                f"({100*label.mean():.1f}% positive rate)")
    return label


def run_module4_results() -> pd.DataFrame:
    """Return the Module 4 scored DataFrame with IF columns attached."""
    out = run_module4()
    return out['results']


def run_module5(work_level: pd.DataFrame = None) -> Dict:
    """Train XGBoost + SMOTE, evaluate, return model + metrics + per-work scores."""
    logger.info("=" * 60)
    logger.info("MODULE 5: XGBoost + SMOTE (supervised risk scoring)")
    logger.info("=" * 60)

    if work_level is None:
        df = run_module4_results()
    else:
        df = work_level.copy()

    # ---- attach rule-engine flags (any_hard_violation, bypass_ml, rule cols) ----
    if 'any_hard_violation' not in df.columns:
        rules = run_module3()['work_rules']
        rule_cols = ['any_hard_violation', 'bypass_ml', 'rule_completed_overdue',
                     'rule_pipeline_stale', 'rule_disallowed_category',
                     'rule_allocation_ceiling', 'completed_overdue_days',
                     'completed_overdue_2yr', 'pipeline_stale_days',
                     'allocation_violation_amount', 'allocated_amount']
        rule_cols = [c for c in rule_cols if c in rules.columns]
        df = df.merge(rules[['work_id'] + rule_cols], on='work_id', how='left')

    # ---- derive labels ----
    df['xgb_label'] = _derive_labels(df)

    # ---- select features ----
    feats = [c for c in XGB_FEATURES if c in df.columns]
    logger.info(f"XGBoost features ({len(feats)}): {feats}")

    X_raw = df[feats].apply(pd.to_numeric, errors='coerce')
    y = df['xgb_label'].astype(int)

    # robust median-impute: all-NaN columns fall back to 0
    medians = X_raw.median().fillna(0.0)
    X = X_raw.fillna(medians).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # ---- train/test split (stratified) ----
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
    )
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")
    logger.info(f"Train positive rate: {y_train.mean():.3f} | Test positive rate: {y_test.mean():.3f}")

    # ---- SMOTE + XGBoost pipeline ----
    n_pos = int(y_train.sum())
    smote_frac = max(0.5, min(1.0, n_pos / (len(y_train) - n_pos))) if n_pos < len(y_train) - n_pos else 1.0
    logger.info(f"SMOTE target fraction (minority -> 50%%): {smote_frac:.3f}")

    pipeline = ImbPipeline([
        ('smote', SMOTE(random_state=RANDOM_STATE, k_neighbors=min(SMOTE_K_NEIGHBORS, max(1, n_pos - 1)))),
        ('xgb', XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=1.0,  # SMOTE already balances
            eval_metric='logloss',
            random_state=RANDOM_STATE,
            use_label_encoder=False,
        )),
    ])

    pipeline.fit(X_train, y_train)

    # ---- evaluate on test set ----
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary', zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba) if len(np.unique(y_test)) > 1 else np.nan
    cm = confusion_matrix(y_test, y_pred)

    metrics = {
        'test_precision': float(precision),
        'test_recall': float(recall),
        'test_f1': float(f1),
        'test_roc_auc': float(roc_auc),
        'confusion_matrix': cm.tolist(),
        'train_size': len(X_train),
        'test_size': len(X_test),
    }
    logger.info(f"\n=== XGBOOST METRICS (held-out test) ===")
    logger.info(f"  Precision: {precision:.3f}")
    logger.info(f"  Recall:    {recall:.3f}")
    logger.info(f"  F1:        {f1:.3f}")
    logger.info(f"  ROC AUC:   {roc_auc:.3f}")
    logger.info(f"  Confusion matrix:\n{cm}")

    # ---- full-dataset prediction (for Module 7 composite) ----
    xgb_proba_full = pipeline.predict_proba(X)[:, 1]
    df['xgb_risk_probability'] = xgb_proba_full
    df['xgb_predicted'] = pipeline.predict(X)

    # feature importance (from XGBClassifier step)
    xgb_model = pipeline.named_steps['xgb']
    importance = dict(zip(feats, xgb_model.feature_importances_))
    importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    return {
        'results': df,
        'pipeline': pipeline,
        'features': feats,
        'metrics': metrics,
        'feature_importance': importance_sorted,
        'y_test': y_test,
        'y_pred': y_pred,
        'y_proba': y_proba,
        'idx_test': idx_test,
    }


if __name__ == "__main__":
    out = run_module5()
    df = out['results']
    metrics = out['metrics']
    importance = out['feature_importance']

    print("\n" + "=" * 80)
    print("MODULE 5 TEST RESULTS — XGBoost + SMOTE (supervised)")
    print("=" * 80)

    print(f"\n--- Test-set metrics ---")
    for k, v in metrics.items():
        if k == 'confusion_matrix':
            print(f"  {k}:")
            print(f"              Predicted 0   Predicted 1")
            print(f"    Actual 0   {v[0][0]:>8}   {v[0][1]:>8}")
            print(f"    Actual 1   {v[1][0]:>8}   {v[1][1]:>8}")
        else:
            print(f"  {k}: {v}")

    print(f"\n--- Classification report ---")
    y_test = out['y_test']
    y_pred = out['y_pred']
    print(classification_report(y_test, y_pred, zero_division=0))

    print(f"\n--- Feature importance (top 15) ---")
    for feat, imp in importance[:15]:
        bar = '#' * int(imp * 200)
        print(f"  {feat:40s}  {imp:.4f}  {bar}")

    # ---- Risk probabilities for Module 4's same 5 sample works ----
    print(f"\n--- Risk probabilities: 5 known-good works (should be LOW) ---")
    clean_sample = [
        'WS/MP620/2024-2025/133166',
        'WS/MP418/2024-2025/133409',
        'WS/MP577/2025-2026/133549',
        'WS/MP577/2025-2026/133551',
        'WS/MP577/2025-2026/133563',
    ]
    check = df[df['work_id'].isin(clean_sample)][[
        'work_id', 'xgb_risk_probability', 'if_anomaly_score',
        'any_hard_violation', 'xgb_label',
    ]]
    print(check.to_string(index=False))

    print(f"\n--- Risk probabilities: TOP 10 highest XGBoost risk ---")
    top = df.nlargest(10, 'xgb_risk_probability')[[
        'work_id', 'source_table', 'work_category_suffix',
        'sanction_amount', 'total_expenditure', 'days_sanctioned_to_completion',
        'if_anomaly_score', 'xgb_risk_probability', 'any_hard_violation', 'xgb_label',
    ]]
    print(top.to_string(index=False))

    print(f"\n--- Risk probabilities: BOTTOM 5 lowest XGBoost risk ---")
    bot = df.nsmallest(5, 'xgb_risk_probability')[[
        'work_id', 'source_table', 'work_category_suffix',
        'sanction_amount', 'total_expenditure', 'if_anomaly_score',
        'xgb_risk_probability', 'any_hard_violation',
    ]]
    print(bot.to_string(index=False))

    print(f"\n--- XGBoost risk distribution ---")
    print(df['xgb_risk_probability'].describe().to_string())
