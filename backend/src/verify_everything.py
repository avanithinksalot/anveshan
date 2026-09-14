"""
End-to-end verification: run every module and assert the outputs match the
logged/live number set. Print PASS/FAIL per check.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

CHECKS = []
PASSED, FAILED = [], []


def check(name, cond, detail=""):
    CHECKS.append(name)
    (PASSED if cond else FAILED).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))


def section(t):
    print("\n" + "=" * 76)
    print(t)
    print("=" * 76)


# ---------- Module 1 ----------
section("MODULE 1 — Data ingestion")
from src.data_ingestion import run_module1
master, _ = run_module1()
check("Master has 48,925 works", len(master) == 48925, f"got {len(master)}")
n_empty = master['work_id'].isna().sum() + (master['work_id'] == '').sum()
check("work_id present on all sanctioned/completed (empty only for unparseable recommended)",
      (master['work_id'].replace('', np.nan).notna().mean() > 0.99),
      f"{n_empty} empty/NaN of {len(master)}")
check("No footer/malformed retained", not master['work_id'].astype(str).str.lower().str.contains('grand').any())

# ---------- Module 2 ----------
section("MODULE 2 — Feature engineering")
from src.feature_engineering import run_module2
feat = run_module2()
work = feat['work_level']
ven = feat['vendor_level']
mp = feat['mp_level']
check("work_level 48,925 x 42", work.shape == (48925, 42), f"got {work.shape}")
check("vendor_level ~23,106 x 5", ven.shape[0] == 23106 and ven.shape[1] >= 5, f"got {ven.shape}")
check("mp_level 648 x 9", mp.shape == (648, 9), f"got {mp.shape}")
check("sanctioned-based ratios 0 coverage (spec)", 
      work['disbursed_vs_sanctioned_ratio'].notna().sum() == 0)
check("fallback ratios present",
      work['disbursed_vs_recommended_ratio'].notna().sum() == 11818,
      f"got {work['disbursed_vs_recommended_ratio'].notna().sum()}")
check("context-aware disallowed = 64",
      work['disallowed_category_keyword_flag'].sum() == 64,
      f"got {work['disallowed_category_keyword_flag'].sum()}")


# ---------- Module 3 ----------
section("MODULE 3 — Rule engine")
from src.rule_engine import run_module3
r3 = run_module3(feat)
wr = r3['work_rules']
hard = wr['any_hard_violation'].sum()
pstale = wr['rule_pipeline_stale'].sum()
disallowed = wr['rule_disallowed_category'].sum()
check("any_hard_violation = 2,749", hard == 2749, f"got {hard}")
check("completed_overdue = 2,690", wr['rule_completed_overdue'].sum() == 2690)
check("completed_overdue_2yr = 0", wr['completed_overdue_2yr'].sum() == 0, "extension band empty, as logged")
check("pipeline_stale = 11,859", pstale == 11859, f"got {pstale}")
check("disallowed = 64", disallowed == 64, f"got {disallowed}")
check("allocation_ceiling = 0", wr['rule_allocation_ceiling'].sum() == 0)
clean_sample = ['WS/MP620/2024-2025/133166', 'WS/MP418/2024-2025/133409',
                'WS/MP577/2025-2026/133549', 'WS/MP577/2025-2026/133551',
                'WS/MP577/2025-2026/133563']
cs = wr[wr['work_id'].isin(clean_sample)]['any_hard_violation']
check("zero-false-trigger on 5 compliant works", cs.eq(0).all(), dict(cs.astype(int)))


# ---------- Module 4 ----------
section("MODULE 4 — Isolation Forest")
from src.isolation_forest import run_module4
r4 = run_module4(work_level=work, vendor_level=ven)
w4 = r4['results']
ifscore = w4['if_anomaly_score']
check("IF covers all works", len(w4) == 48925)
check("score range 0..1", ifscore.min() >= 0 and ifscore.max() <= 1.0,
      f"[{ifscore.min():.3f}, {ifscore.max():.3f}]")
check("~5% predicted outliers", 0.02 <= w4['if_predicted_outlier'].mean() <= 0.08,
      f"{w4['if_predicted_outlier'].mean():.3f}")
known_if = w4[w4['work_id'].isin(clean_sample)]['if_anomaly_score'].max()
check("compliant works IF <= 0.397", known_if <= 0.397, f"{known_if:.4f}")


# ---------- Module 5 ----------
section("MODULE 5 — XGBoost + SMOTE")
from src.xgboost_model import run_module5
r5 = run_module5(work_level=w4)
w5 = r5['results']
m5 = r5['metrics']
check("XGB covered", 'xgb_risk_probability' in w5.columns and len(w5) == 48925)
prec, rec = m5['test_precision'], m5['test_recall']
check("Precision >= 0.99", prec >= 0.99, f"{prec:.4f}")
check("Recall >= 0.98", rec >= 0.98, f"{rec:.4f}")
check("compliant works XGB <= 0.0018",
      w5[w5['work_id'].isin(clean_sample)]['xgb_risk_probability'].max() <= 0.0018)


# ---------- Module 6 ----------
section("MODULE 6 — SHAP explainability")
from src.shap_explain import run_module6
r6 = run_module6(df=w5, pipeline=r5['pipeline'], features=r5['features'])
w6 = r6['results']
check("shap_reason strings present", w6['shap_reason'].notna().sum() == len(w6))
flag_reasons = w6[w6['xgb_risk_probability'] >= 0.5]['shap_reason']
benign = w6[w6['xgb_risk_probability'] < 0.5]['shap_reason']
check(">=0.5 works have substantive reasons",
      flag_reasons.str.contains('flagged|High-risk|outlier|1-year|vendor', case=False, na=False).mean() > 0.5,
      f"{flag_reasons.str.contains('flagged|High-risk|outlier|1-year', case=False, na=False).mean():.2f}")
check("benign works read benign",
      benign.str.contains('No material risk signal', na=False).mean() > 0.8,
      f"{benign.str.contains('No material risk signal', na=False).mean():.2f}")


# ---------- Module 7 ----------
section("MODULE 7 — Composite risk + tiers (standalone: similarity placeholder 0.0)")
from src.composite_score import run_module7
r7 = run_module7(df=w6)
w7 = r7['results']
t7 = w7['risk_tier'].value_counts().to_dict()
check("standalone tiers: Low 45,654 / Med 355 / High 2,916",
      t7.get('Low') == 45654 and t7.get('Medium') == 355 and t7.get('High') == 2916,
      f"got {t7}")
check("bypass_ml == 2,749", int(w7['bypass_ml'].sum()) == 2749)
check("bypass <=> score >= 80", ((w7['bypass_ml'] == 1) == (w7['risk_score'] >= 80)).all())
check("no ML score above 99 (bypass owns the top band)",
      w7[w7['bypass_ml'] == 0]['risk_score'].max() < 100)
check("compliant works all Low",
      w7[w7['work_id'].isin(clean_sample)]['risk_tier'].eq('Low').all())
check("tier boundaries respected",
      ((w7['risk_tier'] == 'High') | (w7['risk_score'] < 70)).all() and
      ((w7['risk_tier'] == 'Medium') | (w7['risk_score'] < 40) | (w7['risk_tier'] == 'High')).all())


# ---------- Module 8 ----------
section("MODULE 8 — Text similarity")
from src.text_similarity import run_module8
r8 = run_module8(df=w7)   # reuse Module 7 frame, avoid re-running pipeline
w8 = r8['results']
pairs = r8['pairs']
check("2,000 within-IDA candidate pairs", len(pairs) == 2000, f"got {len(pairs)}")
check("all candidate pairs cos >= 0.60", (pairs['cosine'] >= 0.60).all())
check("439 works with similarity > 0",
      int((w8['similarity_score'] > 0).sum()) == 439, f"got {(w8['similarity_score']>0).sum()}")
check("compliant works similarity 0",
      w8[w8['work_id'].isin(clean_sample)]['similarity_score'].eq(0).all())
check("top pairs rapidfuzz-confirmed",
      (pairs.head(20)['fuzzy_token_set_ratio'] >= 70).all())

section("MODULE 7 FINAL — composite RE-SCORED with Module 8 similarity populated")
from src.composite_score import _compute_scores
w7f = _compute_scores(w8)
t7f = w7f['risk_tier'].value_counts().to_dict()
check("final tiers: Low 45,654 / Med 353 / High 2,918",
      t7f.get('Low') == 45654 and t7f.get('Medium') == 353 and t7f.get('High') == 2918,
      f"got {t7f}")
check("bypass contract preserved after re-score",
      int(w7f['bypass_ml'].sum()) == 2749 and
      ((w7f['bypass_ml'] == 1) == (w7f['risk_score'] >= 80)).all())
check("compliant works still Low after re-score",
      w7f[w7f['work_id'].isin(clean_sample)]['risk_tier'].eq('Low').all())


# ---------- Module 9 ----------
section("MODULE 9 — Perceptual image hashing")
from src.image_hashing import run_module9
r9 = run_module9()
s9 = r9['summary']
dup = r9['duplicate_pairs']
check("3 duplicate pairs expected/detected", len(dup) == 3, f"got {len(dup)}")
st = set()
for r in dup.itertuples():
    st.add(tuple(sorted((r.id_a.replace('SYN-', ''), r.id_b.replace('SYN-', '')))))
expect = {('site_a', 'site_a_copy'), ('site_a', 'site_a_near'), ('site_a_copy', 'site_a_near')}
fp = {p for p in st if 'site_a' not in p[0] or 'site_a' not in p[1]}
check("no false positives on distinct scenes", len(fp) == 0, f"FPs: {fp}")
check("expected set matches", st == expect, f"got {st}")

# ---------- summary ----------
section("SUMMARY")
n_pass, n_fail = len(PASSED), len(FAILED)
print(f"\nPassed {n_pass} | Failed {n_fail} | Total {len(CHECKS)}")
for f in FAILED:
    print(f"  FAILED: {f}")
print("END-TO-END VERIFICATION COMPLETE")