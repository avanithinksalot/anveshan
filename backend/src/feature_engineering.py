"""
Module 2: Feature Engineering
Computes features at three granularities:
- Work-level (from master lifecycle table)
- Vendor-level (from expenditure)
- MP/scheme-level (from sanctioned + allocated + calamity)

Note on data joins: the six source tables cover disjoint work_id sets
(as discovered in Module 1), so work-level features rely primarily on
within-table computation. Vendor-level features aggregate the expenditure
table independently. MP/scheme-level features aggregate by MP where a join
key exists.
"""

import re
import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, List, Optional

from src.data_ingestion import (
    load_and_clean_csv,
    join_lifecycle_tables,
    find_col,
    DATA_DIR,
    FILE_MAP,
    clean_indian_number,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DISOLLOWED_CATEGORY_KEYWORDS = [
    'church', 'mosque', 'temple', 'gurudwara', 'gurdwara', 'mandir',
    'religious', 'worship', 'prayer', 'masjid', 'shrine', 'cemetery',
    'cremation', 'burial', 'graveyard', 'idol', 'statue', 'memorial',
    'portrait', 'private residential', 'personal use', 'private building',
    'political', 'party office',
]

# Position words that indicate a keyword is being used as a LANDMARK
# (e.g. "Community Hall NEAR Temple") rather than as the constructed item.
LANDMARK_WORDS = {
    'near', 'beside', 'besides', 'opposite', 'adjacent', 'behind',
    'around', 'nearby', 'close', 'beyond', 'towards', 'outside',
    'infront', 'next', 'opprantive', 'premises', 'vicinity',
}

# Construction verbs that make a following restricted keyword the OBJECT
# of the work (e.g. "construction of temple", "mandir nirman").
CONSTRUCTION_VERBS = {
    'construction', 'construct', 'erection', 'erecting', 'renovation',
    'renovat', 'reconstruction', 'rebuild', 'repair', 'develop',
    'development', 'build', 'building', 'creating', 'creation',
    'installation', 'install', 'establish', 'nirman', 'nirmana',
    'karya', 'kaam', 'work',
}

# Authoritative categories that are public works with route/infrastructure
# intent. A restricted keyword in such a description is a ROUTE/landmark
# reference (e.g. "CC road ... to Shiv temple" is an allowed road work), not
# the constructed object.
ALLOWED_INFRASTRUCTURE_TERMS = (
    'road', 'pathway', 'path', 'drainage', 'culvert', 'bridge',
    'paving', 'interlocking', 'pcc', 'cc road', 'highway', 'street',
)

def detect_disallowed_category_flag(description, category_suffix="") -> int:
    """Context-aware detection of disallowed work categories.

    A disallowed keyword only flags the work when it is the OBJECT of
    construction (e.g. "Construction of Temple") rather than a surrounding
    LANDMARK reference (e.g. "Community Hall NEAR Mallikarjun Temple") or a
    category-sanctioned domain. If the authoritative work category itself names
    the restricted domain (e.g. the *allowed* MPLADS category
    "Crematoriums/energy efficient crematoriums or structures on burial/
    cremation ground"), the work is NOT an anomaly.
    """
    if not description:
        return 0
    low = str(description).lower()
    suffix_low = (category_suffix or "").lower()

    # 1) Authoritative category sanctions the domain -> not disallowed.
    for kw in DISOLLOWED_CATEGORY_KEYWORDS:
        if kw in suffix_low:
            return 0
    # 2) Category is a public road/infrastructure work -> keyword is a route
    #    landmark, not the constructed object (e.g. "cc road ... to temple").
    if any(term in suffix_low for term in ALLOWED_INFRASTRUCTURE_TERMS):
        return 0

    tokens = re.findall(r"[a-z]+", low)
    if not tokens:
        return 0

    for i, tok in enumerate(tokens):
        if tok not in DISOLLOWED_CATEGORY_KEYWORDS:
            continue
        # skip landmark usage: a positional word precedes the keyword
        window = tokens[max(0, i - 4):i]
        if any(w in LANDMARK_WORDS for w in window):
            continue
        # flag only if a construction verb is adjacent to the keyword
        lo = max(0, i - 3)
        hi = min(len(tokens), i + 4)
        if any(t in CONSTRUCTION_VERBS for t in tokens[lo:hi]):
            return 1
    return 0

def _matching_keyword(descriptions, category_suffixes) -> List:
    """Return the first disallowed keyword that caused a flag (for debugging)."""
    out = []
    for desc, suffix in zip(descriptions, category_suffixes):
        if not desc:
            out.append("")
            continue
        low = str(desc).lower()
        suffix_low = (suffix or "").lower()
        if any(kw in suffix_low for kw in DISOLLOWED_CATEGORY_KEYWORDS):
            out.append("")
            continue
        if any(term in suffix_low for term in ALLOWED_INFRASTRUCTURE_TERMS):
            out.append("")
            continue
        tokens = re.findall(r"[a-z]+", low)
        match = ""
        for i, tok in enumerate(tokens):
            if tok not in DISOLLOWED_CATEGORY_KEYWORDS:
                continue
            window = tokens[max(0, i - 4):i]
            if any(w in LANDMARK_WORDS for w in window):
                continue
            lo = max(0, i - 3)
            hi = min(len(tokens), i + 4)
            if any(t in CONSTRUCTION_VERBS for t in tokens[lo:hi]):
                match = tok
                break
        out.append(match)
    return out

INDIVIDUAL_VENDOR_KEYWORDS = [
    'shri', 'sh.', 'smt', 'smt.', 'mr.', 'ms.', 'mrs.', 'driver',
    'contractor', 'supplier', 'individual', 'proprietor', 'trader',
]

def compute_work_level_features(master: pd.DataFrame) -> pd.DataFrame:
    """Compute work-level features from the master lifecycle table."""
    df = master.copy()

    df['sanction_amount'] = pd.to_numeric(df['sanction_amount'], errors='coerce')
    df['recommended_amount'] = pd.to_numeric(df['recommended_amount'], errors='coerce')
    df['amount_disbursed'] = pd.to_numeric(df['amount_disbursed'], errors='coerce')
    df['total_expenditure'] = pd.to_numeric(df['total_expenditure'], errors='coerce')

    df['sanction_date'] = pd.to_datetime(df['sanction_date'], errors='coerce', format='%d-%b-%Y')
    df['completion_date'] = pd.to_datetime(df['completion_date'], errors='coerce', format='%d-%b-%Y')
    df['recommended_date'] = pd.to_datetime(df['recommended_date'], errors='coerce', format='%d-%b-%Y')

    # disbursed_vs_sanctioned_ratio
    df['disbursed_vs_sanctioned_ratio'] = np.where(
        df['sanction_amount'] > 0,
        df['amount_disbursed'] / df['sanction_amount'],
        np.nan,
    )

    # Where no explicit sanction_amount but an amount_disbursed exists, use
    # total_expenditure as the disbursed proxy for ratio computations.
    df['expenditure_vs_sanctioned_ratio'] = np.where(
        df['sanction_amount'] > 0,
        df['total_expenditure'] / df['sanction_amount'],
        np.nan,
    )

    # sanction_vs_recommended_diff_pct
    df['sanction_vs_recommended_diff_pct'] = np.where(
        df['recommended_amount'] > 0,
        (df['sanction_amount'] - df['recommended_amount']) / df['recommended_amount'] * 100,
        np.nan,
    )

    # --- Fallback ratios that ARE computable on the overlapping tables ---
    # The Sanctioned table is disjoint from Recommended/Completed/Expenditure,
    # so the spec's sanctioned-based ratios are 0% on real data. These give the
    # risk engine real signal on the 11,838 recommended->completed works and the
    # 35,121 completed<->expenditure works.
    df['disbursed_vs_recommended_ratio'] = np.where(
        df['recommended_amount'] > 0,
        df['amount_disbursed'] / df['recommended_amount'],
        np.nan,
    )
    df['expenditure_vs_recommended_ratio'] = np.where(
        df['recommended_amount'] > 0,
        df['total_expenditure'] / df['recommended_amount'],
        np.nan,
    )
    df['expenditure_vs_disbursed_ratio'] = np.where(
        df['amount_disbursed'] > 0,
        df['total_expenditure'] / df['amount_disbursed'],
        np.nan,
    )
    df['disbursed_overrun_flag'] = (
        (df['expenditure_vs_disbursed_ratio'] > 1.2)
        | (df['expenditure_vs_recommended_ratio'] > 1.2)
    ).astype(int)
    df.loc[
        (df['expenditure_vs_disbursed_ratio'].isna())
        & (df['expenditure_vs_recommended_ratio'].isna()),
        'disbursed_overrun_flag',
    ] = np.nan

    # days_sanctioned_to_completion
    df['days_sanctioned_to_completion'] = (df['completion_date'] - df['sanction_date']).dt.days

    # is_overdue_1yr_rule (completion > 365 days from sanction)
    df['is_overdue_1yr_rule'] = (df['days_sanctioned_to_completion'] > 365).astype(int)
    df.loc[df['days_sanctioned_to_completion'].isna(), 'is_overdue_1yr_rule'] = np.nan

    # work_status_stage_duration (days in current stage from sanction date)
    today = pd.Timestamp.now()
    df['work_status_stage_duration'] = (today - df['sanction_date']).dt.days

    # duplicate_work_id_flag (same work_id appearing multiple times)
    df['duplicate_work_id_flag'] = df['work_id'].duplicated(keep=False).astype(int)

    # image_missing_flag
    df['image_missing_flag'] = df['image_url'].isna().astype(int)

    # disallowed_category_keyword_flag (context-aware: flags only when the
    # restricted object is the ITEM being constructed, not a landmark nearby,
    # and not when the authoritative work category sanctions the domain)
    if 'work_category_suffix' not in df.columns:
        df['work_category_suffix'] = ''
    df['work_category_suffix'] = df['work_category_suffix'].fillna('').astype(str)
    df['disallowed_category_keyword_flag'] = [
        detect_disallowed_category_flag(d, s)
        for d, s in zip(df['work_description'].fillna('').astype(str),
                        df['work_category_suffix'])
    ]
    df['disallowed_keyword_match'] = _matching_keyword(
        df['work_description'].fillna('').astype(str).tolist(),
        df['work_category_suffix'].tolist(),
    )

    # ---- z-score of sanction amount within work category ----
    cat_means = df.groupby('work_category')['sanction_amount'].transform('mean')
    cat_stds = df.groupby('work_category')['sanction_amount'].transform('std')
    df['amount_zscore_in_category'] = (df['sanction_amount'] - cat_means) / cat_stds.replace(0, np.nan)

    logger.info(f"Work-level features computed: {df.shape}")
    return df


def compute_vendor_level_features(expenditure: pd.DataFrame) -> pd.DataFrame:
    """Compute vendor-level features from the expenditure table."""
    df = expenditure.copy()

    vendor_col = None
    for col in df.columns:
        if 'vendor' in col.lower():
            vendor_col = col
            break
    ida_col = None
    for col in df.columns:
        if col.lower() == 'ida':
            ida_col = col
            break

    if not vendor_col:
        logger.error("No vendor column found in expenditure")
        return pd.DataFrame()

    df['vendor_clean'] = df[vendor_col].fillna('').astype(str).str.strip().str.upper()

    # Drop blanks
    df = df[df['vendor_clean'] != ''].copy()

    # vendor_ida_count — number of distinct IDAs a vendor appears in
    vendor_ida = df.groupby('vendor_clean')[ida_col].nunique().rename('vendor_ida_count')

    # vendor_mp_count — number of distinct MPs a vendor appears for
    mp_col = None
    for col in df.columns:
        if 'parliament' in col.lower() or 'mp' == col.lower():
            mp_col = col
            break
    if mp_col:
        vendor_mp = df.groupby('vendor_clean')[mp_col].nunique().rename('vendor_mp_count')
    else:
        vendor_mp = pd.Series(0, index=df['vendor_clean'].unique(), name='vendor_mp_count')

    # vendor_is_individual_flag
    vendor_is_indiv = df['vendor_clean'].apply(
        lambda v: 1 if any(k.lower() in v.lower() for k in INDIVIDUAL_VENDOR_KEYWORDS) else 0
    ).groupby(df['vendor_clean']).max().rename('vendor_is_individual_flag')

    # vendor_concentration_score — within a vendor, max share of total expenditure
    amt_col = None
    for col in df.columns:
        if 'fund disbursed' in col.lower():
            amt_col = col
            break
    if amt_col:
        df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')
        vendor_total = df.groupby('vendor_clean')[amt_col].sum().rename('vendor_total_amount')
        total_amount = df[amt_col].sum()
        vendor_concentration = (vendor_total / total_amount).rename('vendor_concentration_score')
    else:
        vendor_concentration = pd.Series(np.nan, index=df['vendor_clean'].unique(), name='vendor_concentration_score')

    result = pd.concat([vendor_ida, vendor_mp, vendor_is_indiv, vendor_concentration], axis=1)
    result = result.reset_index()
    result = result.rename(columns={'vendor_clean': 'vendor_name'})

    logger.info(f"Vendor-level features computed: {result.shape}")
    return result


MEMBERSHIP_MARKERS = ['sc', 'st', 'scheduled']

def norm_mp(name):
    """Normalize an MP name: strip title + tenure, uppercase."""
    if pd.isna(name) or not isinstance(name, str):
        return None
    n = re.sub(r'\(.*?\)', '', name.strip())
    n = re.sub(r'\b(Shri|Dr\.?|Smt\.?|Mr\.?|Mrs\.?|Ms\.?)\b', '', n, flags=re.IGNORECASE)
    n = re.sub(r'[^A-Za-z ]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip().upper()
    return n

def compute_mp_scheme_level_features(
    master: pd.DataFrame,
    allocated: pd.DataFrame,
    calamity: pd.DataFrame,
) -> pd.DataFrame:
    """Compute MP/scheme-level features across the full work population."""
    work = master.copy()

    mp_col = 'mp_name'
    if mp_col not in work.columns:
        logger.error("No MP column in master")
        return pd.DataFrame()

    alloc_amount_col = None
    for col in allocated.columns:
        if 'allocated amount' in col.lower():
            alloc_amount_col = col
            break

    cal_amount_col = None
    for col in calamity.columns:
        if 'consent amount' in col.lower():
            cal_amount_col = col
            break

    work['mp_norm'] = work[mp_col].apply(norm_mp)

    sanction_amt_col = find_col(work, ['sanction_amount'])
    if not sanction_amt_col:
        logger.error("No sanction amount in master")
        return pd.DataFrame()

    # MP aggregate of sanctioned amounts (all works, not just sanctioned table)
    work['sanction_amt_num'] = pd.to_numeric(work[sanction_amt_col], errors='coerce')
    mp_sanctioned = work.groupby('mp_norm')['sanction_amt_num'].sum().rename('mp_total_sanctioned')

    if alloc_amount_col:
        alloc_mp_col = find_col(allocated, ["Hon'ble Members of Parliaments", "Hon'ble Members of Parliament", 'MP'])
        if alloc_mp_col:
            allocated['mp_norm'] = allocated[alloc_mp_col].apply(norm_mp)
            mp_alloc = allocated.groupby('mp_norm')[alloc_amount_col].sum().rename('mp_allocated_amount')
        else:
            mp_alloc = pd.Series(np.nan, name='mp_allocated_amount')
    else:
        mp_alloc = pd.Series(np.nan, name='mp_allocated_amount')

    # SC/ST allocation compliance ratio — fraction of works under SC/ST IDA/constituency
    def is_sc_st(row):
        parts = []
        for c in ['ida', mp_col, 'constituency']:
            if c in row.index:
                v = row[c]
                if pd.notna(v):
                    parts.append(str(v))
        s = ' '.join(parts)
        return 1 if any(m in s.lower() for m in MEMBERSHIP_MARKERS) else 0
    work['is_sc_st_work'] = work.apply(is_sc_st, axis=1)

    # calamity_vs_allocation_check
    if cal_amount_col:
        cal_mp_col = find_col(calamity, ["Hon'ble Members of Parliament", 'MP'])
        if cal_mp_col:
            calamity['mp_norm'] = calamity[cal_mp_col].apply(norm_mp)
            cal_agg = calamity.groupby('mp_norm')[cal_amount_col].sum().rename('mp_calamity_consent')
        else:
            cal_agg = pd.Series(np.nan, name='mp_calamity_consent')
    else:
        cal_agg = pd.Series(np.nan, name='mp_calamity_consent')

    mp_feat = pd.DataFrame(index=mp_sanctioned.index)
    mp_feat['mp_total_sanctioned'] = mp_sanctioned
    mp_feat['mp_allocated_amount'] = mp_alloc.reindex(mp_feat.index)
    mp_feat['allocation_utilization_ratio'] = np.where(
        mp_feat['mp_allocated_amount'] > 0,
        mp_feat['mp_total_sanctioned'] / mp_feat['mp_allocated_amount'],
        np.nan,
    )
    mp_feat['mp_sc_st_work_count'] = work.groupby('mp_norm')['is_sc_st_work'].sum()
    mp_feat['mp_total_works'] = work.groupby('mp_norm').size()
    mp_feat['sc_st_allocation_compliance_ratio'] = mp_feat['mp_sc_st_work_count'] / mp_feat['mp_total_works'].replace(0, np.nan)
    mp_feat['mp_calamity_consent'] = cal_agg.reindex(mp_feat.index)
    mp_feat['calamity_vs_allocation_check'] = np.where(
        mp_feat['mp_allocated_amount'] > 0,
        mp_feat['mp_calamity_consent'] / mp_feat['mp_allocated_amount'],
        np.nan,
    )

    mp_feat = mp_feat.reset_index().rename(columns={'index': 'mp_norm'})
    logger.info(f"MP/scheme-level features computed: {mp_feat.shape}")
    return mp_feat


def run_module2() -> Dict[str, pd.DataFrame]:
    """Run Module 2: Feature engineering."""
    logger.info("=" * 60)
    logger.info("MODULE 2: Feature Engineering")
    logger.info("=" * 60)

    dataframes = {}
    for key, filename in FILE_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue
        df, stats = load_and_clean_csv(filepath, key)
        dataframes[key] = df

    master = join_lifecycle_tables(dataframes)

    work_level = compute_work_level_features(master)

    expenditure = dataframes['expenditure']
    vendor_level = compute_vendor_level_features(expenditure)

    sanctioned = dataframes['works_sanctioned']
    allocated = dataframes['allocated_limit_1']
    calamity = dataframes['calamity']
    mp_level = compute_mp_scheme_level_features(master, allocated, calamity)

    logger.info(f"\n=== FEATURE SUMMARY ===")
    logger.info(f"Work-level: {work_level.shape}")
    logger.info(f"Vendor-level: {vendor_level.shape}")
    logger.info(f"MP-level: {mp_level.shape}")

    return {
        'work_level': work_level,
        'vendor_level': vendor_level,
        'mp_level': mp_level,
    }


if __name__ == "__main__":
    features = run_module2()

    print("\n" + "=" * 80)
    print("MODULE 2 TEST RESULTS")
    print("=" * 80)

    work = features['work_level']
    vendor = features['vendor_level']
    mp = features['mp_level']

    work_feat_cols = ['work_id', 'source_table', 'work_category', 'sanction_amount',
                      'recommended_amount', 'amount_disbursed', 'total_expenditure',
                      'disbursed_vs_sanctioned_ratio', 'expenditure_vs_sanctioned_ratio',
                      'disbursed_vs_recommended_ratio', 'expenditure_vs_recommended_ratio',
                      'expenditure_vs_disbursed_ratio', 'disbursed_overrun_flag',
                      'sanction_vs_recommended_diff_pct', 'amount_zscore_in_category',
                      'days_sanctioned_to_completion', 'is_overdue_1yr_rule',
                      'work_status_stage_duration', 'duplicate_work_id_flag',
                      'image_missing_flag', 'disallowed_category_keyword_flag']
    work_feat_cols = [c for c in work_feat_cols if c in work.columns]

    print("\n--- WORK-LEVEL FEATURES ---")
    print(f"Shape: {work.shape}")

    print("\n### Sample 10 works (as they appear) ###")
    print(work[work_feat_cols].head(10).to_string())

    print("\n### Clearly-RISKY work samples (disallowed keyword / overdue / missing image) ###")
    risky_mask = (
        (work['disallowed_category_keyword_flag'] == 1)
        | (work['is_overdue_1yr_rule'] == 1)
    )
    risky = work[risky_mask].dropna(subset=['work_description'])
    if len(risky) > 0:
        show_cols = ['work_id', 'work_category', 'work_category_suffix', 'work_description',
                     'days_sanctioned_to_completion', 'is_overdue_1yr_rule',
                     'disallowed_category_keyword_flag', 'disallowed_keyword_match',
                     'image_missing_flag']
        show_cols = [c for c in show_cols if c in risky.columns]
        print(risky[show_cols].head(6).to_string())
    else:
        print("(none found in current data)")

    print("\n### Disallowed-flag: old naive vs new context-aware ###")
    desc_naive = work['work_description'].fillna('').astype(str)
    naive_flags = desc_naive.apply(
        lambda s: 1 if any(k.lower() in s.lower() for k in DISOLLOWED_CATEGORY_KEYWORDS) else 0
    )
    print(f"  Old naive flag = 1:  {int(naive_flags.sum())} works")
    print(f"  New context-aware = 1: {int(work['disallowed_category_keyword_flag'].sum())} works")
    print("  Newly unflagged examples (were false positives before):")
    diff = work.index[naive_flags == 1].tolist()
    unflagged = work.loc[diff][work.loc[diff, 'disallowed_category_keyword_flag'] == 0]
    if len(unflagged) > 0:
        ucols = ['work_id', 'work_category_suffix', 'work_description']
        ucols = [c for c in ucols if c in unflagged.columns]
        print(unflagged[ucols].head(5).to_string())
    print("  Newly flagged examples (primary religious/restricted construction):")
    flagged = work[work['disallowed_category_keyword_flag'] == 1]
    if len(flagged) > 0:
        fcols = ['work_id', 'work_category_suffix', 'work_description', 'disallowed_keyword_match']
        fcols = [c for c in fcols if c in flagged.columns]
        print(flagged[fcols].head(8).to_string())
    else:
        print("(none in current data)")

    print("\n### Clearly-COMPLIANT work samples ###")
    clean_mask = (
        (work['disallowed_category_keyword_flag'] == 0)
        & (work['is_overdue_1yr_rule'] == 0)
        & (work['image_missing_flag'] == 0)
        & (work['amount_disbursed'].notna())
    )
    clean = work[clean_mask]
    if len(clean) > 0:
        print(clean[work_feat_cols].head(6).to_string())
    else:
        print("(none found - image_missing_flag is 1 for works without an image URL; showing unflagged instead)")
        clean = work[
            (work['disallowed_category_keyword_flag'] == 0)
            & (work['is_overdue_1yr_rule'] == 0)
            & (work['amount_disbursed'].notna())
        ]
        print(clean[work_feat_cols].head(6).to_string())

    print("\n--- VENDOR-LEVEL FEATURES ---")
    print(f"Shape: {vendor.shape}")
    print("\nTop vendors by concentration score (potential red flags):")
    top_vendors = vendor.nlargest(8, 'vendor_concentration_score')
    print(top_vendors.to_string())
    print("\nSample 5 vendors:")
    print(vendor.head(5).to_string())

    print("\n--- MP/SCHEME-LEVEL FEATURES ---")
    print(f"Shape: {mp.shape}")
    print("\nMPs with highest sanctioned totals:")
    print(mp.nlargest(5, 'mp_total_sanctioned')[['mp_norm', 'mp_total_sanctioned', 'mp_allocated_amount',
                                                  'allocation_utilization_ratio', 'mp_total_works',
                                                  'sc_st_allocation_compliance_ratio']].to_string())

    print("\n--- Feature coverage (work-level) ---")
    for col in ['disbursed_vs_sanctioned_ratio', 'expenditure_vs_sanctioned_ratio',
                'disbursed_vs_recommended_ratio', 'expenditure_vs_recommended_ratio',
                'expenditure_vs_disbursed_ratio', 'disbursed_overrun_flag',
                'sanction_vs_recommended_diff_pct',
                'amount_zscore_in_category', 'days_sanctioned_to_completion',
                'is_overdue_1yr_rule', 'work_status_stage_duration',
                'duplicate_work_id_flag', 'image_missing_flag', 'disallowed_category_keyword_flag']:
        if col in work.columns:
            n = work[col].notna().sum()
            pct = 100.0 * n / len(work) if len(work) else 0
            print(f"  {col}: {n}/{len(work)} non-null ({pct:.1f}%)")

    print("\n### Samples where expenditure exceeds disbursed (overrun risk) ###")
    overrun = work[work['disbursed_overrun_flag'] == 1]
    if len(overrun) > 0:
        oc = ['work_id', 'recommended_amount', 'amount_disbursed', 'total_expenditure',
              'expenditure_vs_recommended_ratio', 'expenditure_vs_disbursed_ratio']
        oc = [c for c in oc if c in overrun.columns]
        print(overrun[oc].head(8).to_string())
    else:
        print("(none in current data)")