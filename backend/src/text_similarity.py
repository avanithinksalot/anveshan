"""
Module 8: Text similarity (duplicate / near-duplicate work detection)

Approach per spec: TF-IDF + cosine similarity for exact numeric ranking,
rapidfuzz for fast fuzzy confirmation of flagged candidate pairs.

Because full all-pairs over 48,925 works is ~2.4B pairs (intractable and
mostly meaningless across districts), similarity is computed WITHIN each IDA
(district authority) group only as the primary scope:
  - a genuine duplicate/misreported work would recur under the same district;
  - the largest IDA group is 1,203 works -> at most ~720k cosine pairs per
    group, vectorised cheaply.
There is one global TF-IDF model (shared vocabulary), so cross-IDA works can
be compared later if needed.

Outputs:
  results        Module 7 scored frame + `similarity_score` (per work: max
                 cosine to ANY other work in the same IDA; 0 when isolated),
                 which feeds the composite's 20% slot (currently placeholder 0).
  pairs          top candidate pairs: work_id, IDA, cosine, rapidfuzz
                 token_set_ratio, and both descriptions for human review.

Thresholds:
  DUP_CANDIDATE  cosine >= 0.80  (near-duplicate works worth an auditor's look)
  REVIEW         cosine >= 0.60  (similar works, surfaced in the report)
"""

import logging
import re
import numpy as np
import pandas as pd
from typing import Dict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

from src.composite_score import run_module7

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

COSINE_DUP_CANDIDATE = 0.80
COSINE_REVIEW = 0.60
FUZZY_CROSS_CHECK = 70  # rapidfuzz token_set_ratio threshold to "confirm"


def _clean(desc: str) -> str:
    """Lowercase, collapse whitespace, keep letters/digits."""
    if not isinstance(desc, str):
        return ""
    s = desc.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _tfidf_matrix(descs: pd.Series) -> tuple:
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000)
    X = vec.fit_transform(descs)
    return vec, X


def _within_ida_pairs(df: pd.DataFrame, X) -> pd.DataFrame:
    """Top cosine pairs within each IDA group (vectorised)."""
    rows = []
    for ida, group in df.groupby('ida'):
        if len(group) < 2:
            continue
        idx = group.index
        M = cosine_similarity(X[idx])
        M[np.triu_indices(M.shape[0])] = -1.0  # keep strictly lower triangle
        pairs = np.argwhere(M >= COSINE_REVIEW)
        for i, j in pairs:
            ida_local = df.loc[idx[i], 'work_id'], df.loc[idx[j], 'work_id']
            rows.append({
                'id_a': ida_local[0],
                'id_b': ida_local[1],
                'ida': ida,
                'cosine': float(M[i, j]),
            })
    pairs = pd.DataFrame(rows)
    if len(pairs) == 0:
        return pairs
    pairs = pairs.sort_values('cosine', ascending=False).reset_index(drop=True)
    return pairs


def _attach_descriptions(pairs: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    desc = df[['work_id', 'work_description']].drop_duplicates('work_id').set_index('work_id')
    for col, key in [('desc_a', 'id_a'), ('desc_b', 'id_b')]:
        pairs[col] = pairs[key].map(desc['work_description'])
    return pairs


def _rapidfuzz_cross_check(pairs: pd.DataFrame, top_n: int = 2000) -> pd.DataFrame:
    """Confirm flagged pairs with rapidfuzz token_set_ratio."""
    pairs = pairs.head(top_n).copy()
    ratios = []
    for _, r in pairs.iterrows():
        a = str(r['desc_a']) if pd.notna(r['desc_a']) else ''
        b = str(r['desc_b']) if pd.notna(r['desc_b']) else ''
        ratios.append(fuzz.token_set_ratio(_clean(a), _clean(b)))
    pairs['fuzzy_token_set_ratio'] = ratios
    return pairs


def _per_work_max_similarity(pairs: pd.DataFrame, df: pd.DataFrame) -> pd.Series:
    """similarity_score per work = max cosine among its within-IDA pairs."""
    sim = pd.Series(0.0, index=df.index)
    if len(pairs) == 0:
        return sim
    work_to_sim = df[['work_id']].copy()
    p = pairs[['id_a', 'id_b', 'cosine']]
    long = pd.concat([
        p.rename(columns={'id_a': 'work_id', 'cosine': 's'}),
        p.rename(columns={'id_b': 'work_id', 'cosine': 's'}),
    ])
    best = long.groupby('work_id')['s'].max()
    sim = df['work_id'].map(best).fillna(0.0)
    sim.index = df.index
    return sim.astype(float)


def run_module8(df: pd.DataFrame = None) -> Dict:
    """Run text similarity; return Module 7 frame + similarity_score + pairs."""
    logger.info("=" * 60)
    logger.info("MODULE 8: Text similarity (duplicate/near-duplicate detection)")
    logger.info("=" * 60)

    if df is None:
        out7 = run_module7()
        df = out7['results']

    work = df.copy()
    before = len(work)
    work = work[work['work_description'].fillna('').astype(str).str.strip() != ''].copy()
    work = work.reset_index(drop=True)
    logger.info(f"{len(work)}/{before} works have a usable description ({before - len(work)} dropped)")

    cleaned = work['work_description'].apply(_clean)
    vec, X = _tfidf_matrix(cleaned)
    logger.info(f"TF-IDF vocab: {len(vec.get_feature_names_out())} terms (1-2 grams, min_df=2)")

    pairs = _within_ida_pairs(work, X)
    logger.info(f"Candidate pairs (cosine >= {COSINE_REVIEW}) within IDA: {len(pairs)}")

    pairs = _attach_descriptions(pairs, work)
    pairs = _rapidfuzz_cross_check(pairs)

    sim = _per_work_max_similarity(pairs, work)
    work['similarity_score'] = sim
    # re-attach similarity_score to the FULL dataframe (incl. empty-desc works = 0)
    df['similarity_score'] = df['work_id'].map(work[['work_id', 'similarity_score']].set_index('work_id')['similarity_score']).fillna(0.0)

    n_dup_candidates = int((pairs['cosine'] >= COSINE_DUP_CANDIDATE).sum())
    summary = {
        'works_with_desc': len(work),
        'tfidf_vocab': int(len(vec.get_feature_names_out())),
        'candidate_pairs': int(len(pairs)),
        'dup_candidates_cosine_ge_0_80': n_dup_candidates,
        'works_with_any_similarity': int((df['similarity_score'] > 0).sum()),
    }
    logger.info(f"\n=== SIMILARITY SUMMARY ===")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")

    return {'results': df, 'pairs': pairs, 'summary': summary,
            'vectorizer': vec, 'tfidf_matrix': X}


if __name__ == "__main__":
    out = run_module8()
    df = out['results']
    pairs = out['pairs']
    summary = out['summary']

    print("\n" + "=" * 80)
    print("MODULE 8 TEST RESULTS — Text similarity")
    print("=" * 80)

    print(f"\nWorks with description: {summary['works_with_desc']}")
    print(f"TF-IDF vocabulary: {summary['tfidf_vocab']} terms")
    print(f"Within-IDA candidate pairs (cos >= 0.60): {summary['candidate_pairs']}")
    print(f"Near-duplicate candidates (cos >= 0.80): {summary['dup_candidates_cosine_ge_0_80']}")
    print(f"Works with any similarity > 0: {summary['works_with_any_similarity']}")

    print("\n--- TOP 10 highest-cosine pairs (side by side) ---")
    if len(pairs):
        top = pairs.head(10)
        for i, r in enumerate(top.iterrows()):
            r = r[1]
            print(f"\n[{i+1}] cos={r['cosine']:.3f}  fuzzy={r['fuzzy_token_set_ratio']}  IDA={r['ida']}")
            print(f"    A: {r['id_a']} | {str(r['desc_a'])[:100]}")
            print(f"    B: {r['id_b']} | {str(r['desc_b'])[:100]}")
    else:
        print("(no within-IDA pairs above 0.60)")

    print("\n--- DUP-CANDIDATE pairs (cos >= 0.80), first 15 ---")
    dup = pairs[pairs['cosine'] >= COSINE_DUP_CANDIDATE].head(15)
    if len(dup):
        for i, r in enumerate(dup.iterrows()):
            r = r[1]
            print(f"\n[{i+1}] cos={r['cosine']:.3f}  fuzzy={r['fuzzy_token_set_ratio']}")
            print(f"    {r['id_a']}   vs   {r['id_b']}")
            print(f"    {str(r['desc_a'])[:90]}")
            print(f"    {str(r['desc_b'])[:90]}")
    else:
        print("(none)")

    print("\n--- Similarity score distribution (per work) ---")
    print(df['similarity_score'].describe().to_string())
    n_zero = (df['similarity_score'] == 0).sum()
    print(f"Works with similarity_score == 0 (no within-IDA match): {n_zero}")

    print("\n--- SANITY: known-compliant works should have ~0 similarity score ---")
    clean_sample = ['WS/MP620/2024-2025/133166', 'WS/MP418/2024-2025/133409',
                    'WS/MP577/2025-2026/133549', 'WS/MP577/2025-2026/133551',
                    'WS/MP577/2025-2026/133563']
    check = df[df['work_id'].isin(clean_sample)][['work_id', 'similarity_score']]
    print(check.to_string(index=False))

    print("\n--- Verification: similarity_score column ready for Module 7 composite ---")
    print("composite 20% slot reads similarity_score; 'similarity_score' now populated "
          "for " + f"{int((df['similarity_score'] > 0).sum())}" + " works.")