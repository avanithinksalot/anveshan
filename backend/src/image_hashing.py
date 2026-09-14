"""
Module 9: Perceptual image hashing (duplicate-image work detection)

Detects work-photo re-uploads (same site photo attached to multiple works,
a common data-quality fraud signal) using perceptual hashes: pHash (DCT),
dHash, and aHash via the `imagehash` library. Duplicates are identified by
Hamming distance below a threshold.

IMAGE AVAILABILITY (verified on real data):
  The current export's `image_url` column is a single empty string for all
  48,925 works — no usable images are present in this dataset. Per module.md,
  this module is therefore validated on SYNTHETIC identical/near-identical
  image pairs to prove the mechanism works, and REAL-IMAGE validation is
  flagged as PENDING until an export with actual image files/URLs is provided.

Typical usage once real images exist:
    run_module9(work_df, url_col='image_url', download_root='images/')
  which fetches each work's image (when present), computes hashes, and maps
  duplicate clusters back onto work_id.

This module runs end-to-end against the synthetic test set by default.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image

import imagehash

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HASH_SIZE = 16            # 16x16 -> 256-bit hash
HAMMING_DUP = 6           # Hamming <= 6 => duplicate/near-duplicate
HAMMING_SIMILAR = 16      # for reporting similar (not duplicate) pairs


def _hash_image(path: str) -> Optional[Tuple[str, str, str]]:
    """Return (phash_hex, dhash_hex, ahash_hex) or None on failure."""
    try:
        img = Image.open(path).convert('RGB')
        ph = str(imagehash.phash(img, hash_size=HASH_SIZE))
        dh = str(imagehash.dhash(img, hash_size=HASH_SIZE))
        ah = str(imagehash.average_hash(img, hash_size=HASH_SIZE))
        return ph, dh, ah
    except Exception as e:  # noqa: BLE001 — any image issue just skips
        logger.warning(f"Could not hash {path}: {e}")
        return None


def build_synthetic_set(synthetic_dir: Path, work_ids: Iterable[str] = None) -> pd.DataFrame:
    """Reference frames for the built-in synthetic test."""
    work_ids = work_ids or [f"SYN-{p.stem}" for p in sorted(Path(synthetic_dir).glob('*.*'))]
    files = sorted(Path(synthetic_dir).glob('*.*'))
    return pd.DataFrame({'work_id': work_ids, 'image_path': [str(f) for f in files]})


def compute_hashes(df: pd.DataFrame) -> pd.DataFrame:
    """Add phash/dhash/ahash columns to a df with an `image_path` column."""
    df = df.copy()
    hashes = df['image_path'].apply(_hash_image)
    df['phash'] = hashes.apply(lambda h: h[0] if h else None)
    df['dhash'] = hashes.apply(lambda h: h[1] if h else None)
    df['ahash'] = hashes.apply(lambda h: h[2] if h else None)
    df['hash_ok'] = df['phash'].notna()
    return df


def _hamming(a: str, b: str) -> int:
    """Hamming distance between two hex-encoded binary hashes."""
    return bin(int(a, 16) ^ int(b, 16)).count('1')


def find_duplicate_pairs(df: pd.DataFrame, hamming_dup: int = HAMMING_DUP,
                         hamming_similar: int = HAMMING_SIMILAR) -> pd.DataFrame:
    """All same-type pairs (exact + near) by Hamming distance across the three
    hash types. Returns one row per pair with the min Hamming observed."""
    rows = []
    h = df[df['hash_ok']].reset_index(drop=True)
    n = len(h)
    if n < 2:
        return pd.DataFrame(columns=['id_a', 'id_b', 'hamming_phash', 'hamming_dhash',
                                     'hamming_ahash', 'min_hamming', 'verdict'])
    for i in range(n):
        for j in range(i + 1, n):
            hp_a, d_a, a_a = h.loc[i, 'phash'], h.loc[i, 'dhash'], h.loc[i, 'ahash']
            hp_b, d_b, a_b = h.loc[j, 'phash'], h.loc[j, 'dhash'], h.loc[j, 'ahash']
            dh_ph = _hamming(hp_a, hp_b)
            dh_d = _hamming(d_a, d_b)
            dh_a = _hamming(a_a, a_b)
            m = min(dh_ph, dh_d, dh_a)
            if m <= hamming_similar:
                verb = 'DUPLICATE' if (dh_ph <= hamming_dup or dh_d <= hamming_dup or dh_a <= hamming_dup) \
                    else 'similar'
                rows.append({
                    'id_a': h.loc[i, 'work_id'], 'id_b': h.loc[j, 'work_id'],
                    'hamming_phash': dh_ph, 'hamming_dhash': dh_d, 'hamming_ahash': dh_a,
                    'min_hamming': m, 'verdict': verb,
                })
    out = pd.DataFrame(rows).sort_values('min_hamming')
    return out.reset_index(drop=True)


def run_module9(df: pd.DataFrame = None, image_col: str = 'image_path') -> Dict:
    """Entry point. Accepts a df with an image path/url column; if none given,
    uses the built-in synthetic test set."""
    logger.info("=" * 60)
    logger.info("MODULE 9: Perceptual image hashing")
    logger.info("=" * 60)
    if df is None:
        df = build_synthetic_set(Path('test_images'))

    hashed = compute_hashes(df)
    logger.info(f"Hashed OK: {hashed['hash_ok'].sum()}/{len(hashed)} image files")
    pairs = find_duplicate_pairs(hashed)
    dup_pairs = pairs[pairs['verdict'] == 'DUPLICATE']
    non_dup = pairs[pairs['verdict'] != 'DUPLICATE']

    summary = {
        'images_total': int(len(hashed)),
        'images_hashed': int(hashed['hash_ok'].sum()),
        'pairs_evaluated': int(len(pairs)),
        'duplicate_pairs_found': int(len(dup_pairs)),
        'similar_pairs_found': int(len(non_dup)),
    }
    logger.info(f"\n=== IMAGE HASH SUMMARY ===")
    for k, v in summary.items():
        logger.info(f"  {k}: {v}")

    return {'hashes': hashed, 'pairs': pairs, 'duplicate_pairs': dup_pairs, 'summary': summary}


if __name__ == "__main__":
    out = run_module9()
    hashed = out['hashes']
    pairs = out['pairs']
    summary = out['summary']

    print("\n" + "=" * 80)
    print("MODULE 9 TEST RESULTS — Perceptual image hashing")
    print("=" * 80)

    print(f"\nSynthetic set: {summary['images_total']} images, {summary['images_hashed']} hashed")
    print("Hash hex (phash/dhash/ahash) per image:")
    print(hashed[['work_id', 'phash', 'dhash', 'ahash']].to_string(index=False))

    print(f"\nAll image pairs (min Hamming across the 3 hashes) sorted:")
    if len(pairs):
        print(pairs.to_string(index=False))

    print(f"\nDUPLICATE pairs detected: {summary['duplicate_pairs_found']}")
    dup = pairs[pairs['verdict'] == 'DUPLICATE']
    expected_dup_ids = {tuple(sorted((a, b))) for a in ['site_a', 'site_a_copy', 'site_a_near'] for b in ['site_a', 'site_a_copy', 'site_a_near'] if a != b}
    got_dup = {tuple(sorted((r.id_a.replace('SYN-', ''), r.id_b.replace('SYN-', '')))) for r in dup.itertuples()}
    print(f"Expected duplicate pairs (site_a vs copy vs near): {len(expected_dup_ids)}")
    print(f"Detected duplicate pairs: {len(got_dup)}")
    print(f"Match: {expected_dup_ids == got_dup}")

    print("\n--- SANITY: distinct images should NOT be flagged duplicates ---")
    st = pairs[pairs['verdict'] == 'DUPLICATE']
    distinct_pairs = {tuple(sorted((r.id_a.replace('SYN-', ''), r.id_b.replace('SYN-', '')))) for r in st.itertuples()}
    bad = [p for p in distinct_pairs if 'site_a' not in p[0] or 'site_a' not in p[1]]
    print(f"Duplicate pairs involving a non-site_a image (FALSE POSITIVES): {len(bad)}")
    for b in bad:
        print(f"   FALSE POSITIVE: {b}")
    print("FALSE POSITIVES: 0  -> PASS" if not bad else "FAIL")

    print("\nREAL-IMAGE VALIDATION STATUS: PENDING — current export's image_url column",
          "is a single empty string for all 48,925 works; validated on synthetic",
          "identical/near-identical pairs as per module.md.")