"""
Module 6: SHAP explainability layer

Generates per-work plain-language reason strings from SHAP feature attributions
of the Module 5 XGBoost model. Every flagged work in the composite scorer
(Module 7) will carry one of these strings.

Approach:
  - Train a shallow TreeExplainer on the held-out pipeline's trained
    XGBClassifier (imblearn pipeline -> model.named_steps['xgb']).
  - For each work, SHAP values -> the top contributing feature(s) are rendered
    into human-readable clauses like:
      "Flagged due to 340% cost deviation from category median and vendor
       active across 6 districts."
  - Dialects: a small dictionary maps feature names to audit-review phrasing
    with the actual magnitude/context plugged in.

Note: SHAP running TreeExplainer over 48,925 x 19 is fast (tree model).
Missing feature values are already median-imputed in Module 5 (X matrix).
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List

import shap

from src.xgboost_model import run_module5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Feature -> human phrasing template (placeholders: {val}, {other}, etc.)
REASON_TEMPLATES = {
    'if_anomaly_score': 'statistical outlier in cost/timeline/vendor profile (unsupervised score {val:.2f})',
    'is_overdue_1yr_rule': 'completion or pipeline duration breaches the 1-year window',
    'days_sanctioned_to_completion': 'took {val:.0f} days from sanction to completion',
    'image_missing_flag': 'completion photo or image record is missing',
    'sanction_amount': 'sanctioned amount of Rs. {val:,.0f} diverges from normal range',
    'recommended_amount': 'recommended amount of Rs. {val:,.0f} diverges from normal range',
    'total_expenditure': 'total expenditure of Rs. {val:,.0f} diverges from normal range',
    'max_vendor_ida_count': 'vendor footprint spans {val:.0f} districts/IDAs',
    'max_vendor_mp_count': 'vendor works for {val:.0f} different MPs',
    'max_vendor_concentration_score': 'vendor concentration score of {val:.3f} (vendor shares {val:.1%} of total disbursement across the programme)',
    'max_vendor_is_individual_flag': 'a significant vendor is an individual/sole contractor',
    'expenditure_vs_recommended_ratio': 'expenditure is {val:.0%} of the recommended amount',
    'expenditure_vs_disbursed_ratio': 'expenditure is {val:.0%} of the amount disbursed',
    'disbursed_overrun_flag': 'disbursement/expenditure overrun beyond expected ratio',
    'sanction_vs_recommended_diff_pct': 'sanction differs from recommended amount by {val:.0f}%',
    'amount_zscore_in_category': '{val:.1f} standard deviations from the category-mean sanction amount',
    'work_status_stage_duration': 'work has been in a non-terminal stage for {val:.0f} days',
    'duplicate_work_id_flag': 'work_id appears multiple times in source data',
}

# keep only features that actually reached the trained model
FEATURE_DROP = ['xgb_label', 'xgb_risk_probability', 'xgb_predicted', 'bypass_ml',
                'any_hard_violation', 'rule_completed_overdue', 'rule_disallowed_category',
                'rule_allocation_ceiling']


def _prepare_matrix(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    X_raw = df[features].apply(pd.to_numeric, errors='coerce')
    medians = X_raw.median().fillna(0.0)
    X = X_raw.fillna(medians).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return X


def _render_reason(row: pd.Series, shap_values: np.ndarray, features: List[str]) -> str:
    """Build a plain-language reason string from per-feature SHAP contributions.

    Only features with POSITIVE SHAP (pushing the model toward risk=1) are used
    to explain a flag; negative contributions (toward low-risk) are not rendered
    as reasons. Works whose model probability is below 0.5 read as benign.
    """
    contribs = dict(zip(features, shap_values))
    risk = float(row.get('xgb_risk_probability', 0.0))
    hard = int(row.get('any_hard_violation', 0))

    if risk < 0.5 and not hard:
        # benign: report the strongest conservative (negative-SHAP) driver
        mitigants = sorted(contribs.items(), key=lambda x: x[1])  # most negative first
        for feat, shp in mitigants:
            if abs(shp) > 1e-6:
                label = '{:s}'.format(feat.replace('_', ' '))
                return (f"No material risk signal - model probability {risk:.1%}; "
                        f"dominant signal was normal {label}.")
        return f"No material risk signal - model probability {risk:.1%}."

    clauses = []
    for feat, shp in sorted(contribs.items(), key=lambda x: x[1], reverse=True):
        if shp < 1e-6:
            continue
        tpl = REASON_TEMPLATES.get(feat)
        if tpl is None:
            continue
        val = row.get(feat, np.nan)
        try:
            if isinstance(val, (int, float)):
                clause = tpl.format(val=float(val))
            else:
                clause = tpl.replace('{val:.2f}', str(val)).replace('{val:.0f}', str(val)) \
                            .replace('{val:,.0f}', str(val)).replace('{val:.0%}', str(val)) \
                            .replace('{val:.1f}', str(val)).replace('{val:.3f}', str(val))
        except (ValueError, KeyError):
            clause = tpl
        clauses.append(clause)
        if len(clauses) >= 3:
            break
    if not clauses:
        return f"Model risk probability {risk:.1%} with no single feature dominating; review flagged work."
    head = "High-risk work flagged due to " if hard else f"Flagged (model risk {risk:.0%}) due to "
    return head + "; ".join(clauses) + "."


def run_module6(df: pd.DataFrame = None, pipeline: object = None,
                features: List[str] = None) -> Dict:
    """Explain the Module 5 model's per-work reasoning with SHAP.

    Accepts an optional pre-trained pipeline + feature list (e.g. loaded from
    the API layer); otherwise trains Module 5 fresh."""
    logger.info("=" * 60)
    logger.info("MODULE 6: SHAP explainability layer")
    logger.info("=" * 60)

    if df is None or pipeline is None or features is None:
        out5 = run_module5()
        if df is None:
            df = out5['results']
        if pipeline is None:
            pipeline = out5['pipeline']
        if features is None:
            features = out5['features']
    else:
        features = [c for c in features if c in df.columns]

    model = pipeline.named_steps['xgb']
    logger.info(f"Explaining model on {len(df)} works, {len(features)} features")

    X = _prepare_matrix(df, features)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X, check_additivity=False)

    reasons = []
    for i in range(len(df)):
        reasons.append(_render_reason(df.iloc[i], shap_values[i], features))

    df['shap_reason'] = reasons

    # per-feature mean |SHAP| (global importance)
    mean_abs = np.abs(shap_values).mean(axis=0)
    global_importance = dict(zip(features, mean_abs.tolist()))

    summary = {
        'works_explained': int(len(df)),
        'features_explained': features,
        'global_mean_abs_shap': global_importance,
    }
    return {'results': df, 'pipeline': pipeline, 'features': features,
            'shap_values': shap_values, 'summary': summary}


if __name__ == "__main__":
    out = run_module6()
    df = out['results']
    summary = out['summary']

    print("\n" + "=" * 80)
    print("MODULE 6 TEST RESULTS — SHAP explainability layer")
    print("=" * 80)

    print(f"\nWorks explained: {summary['works_explained']}")
    print(f"Features used by SHAP: {summary['features_explained']}")

    print("\n--- Global |SHAP| feature importance ---")
    g = summary['global_mean_abs_shap']
    for feat, v in sorted(g.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feat:40s}  {v:.5f}")

    flagged = df[df['any_hard_violation'] == 1].head(8)
    top_risk = df.nlargest(8, 'xgb_risk_probability')

    print("\n--- Explanation samples: 5 rule-flagged works ---")
    cols = ['work_id', 'work_category_suffix', 'work_description', 'shap_reason']
    for i, (_, r) in enumerate(flagged.head(5).iterrows()):
        print(f"\n[{i+1}] {r['work_id']}")
        print(f"    category : {r['work_category_suffix']}")
        print(f"    desc     : {str(r['work_description'])[:80]}")
        print(f"    REASON   : {r['shap_reason']}")

    print("\n--- Explanation samples: 5 higher-risk non-rule works (ML-only) ---")
    ml_only = df[(df['any_hard_violation'] == 0)].nlargest(5, 'xgb_risk_probability')
    for i, (_, r) in enumerate(ml_only.iterrows()):
        print(f"\n[{i+1}] {r['work_id']}  risk={r['xgb_risk_probability']:.3f}")
        print(f"    category : {r['work_category_suffix']}")
        print(f"    desc     : {str(r['work_description'])[:80]}")
        print(f"    REASON   : {r['shap_reason']}")

    print("\n--- Explanation samples: 3 known-compliant works (should read as benign) ---")
    clean_sample = [
        'WS/MP620/2024-2025/133166',
        'WS/MP418/2024-2025/133409',
        'WS/MP577/2025-2026/133549',
    ]
    clean = df[df['work_id'].isin(clean_sample)]
    for i, (_, r) in enumerate(clean.iterrows()):
        print(f"\n[{i+1}] {r['work_id']}")
        print(f"    category : {r['work_category_suffix']}")
        print(f"    REASON   : {r['shap_reason']}")

    print("\n--- Coverage of reason strings ---")
    has_reason = df['shap_reason'].str.startswith(('Flagged', 'High-risk')).sum()
    print(f"Works with a substantive explanation: {has_reason}/{len(df)}")
    print(f"Benign/empty explanations: {len(df) - has_reason}")
