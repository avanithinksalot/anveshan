"""
Module 1: Data Ingestion + Cleaning
Loads six MPLADS source tables, handles known data-quality issues,
extracts work_id via regex, and joins into master lifecycle table.
"""

import os
import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(os.getenv('MPLADS_DATA_DIR', "D:/IDEs/Visual Studio Code/SIH PS102 MVP/datasets"))

FILE_MAP = {
    "works_recommended": "Works Recommended.csv",
    "works_sanctioned": "Works Sanctioned.csv",
    "works_completed": "Works Completed.csv",
    "expenditure": "Expenditure on Completed and On-going Works as on Date.csv",
    "calamity": "Amount consented for Calamity.csv",
    "allocated_limit_1": "Allocated Limit for Honble MPs.csv",
}

WORK_ID_PATTERN = re.compile(r'(WS/\s*MP[\d]+/\d{4}-\d{4}/\d+)')

INDIAN_NUMBER_PATTERN = re.compile(r'^[\d,\.]+$')

def clean_indian_number(val: str) -> float:
    """Convert Indian comma-formatted numbers (e.g., '17,35,60,04,099.87') to float."""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('nan', 'none', 'null', ''):
        return np.nan
    val_str = val_str.replace(',', '')
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def extract_work_id(work_field: str) -> str:
    """Extract work_id from Work field using regex and normalize."""
    if pd.isna(work_field):
        return None
    match = WORK_ID_PATTERN.search(str(work_field))
    if match:
        work_id = match.group(1)
        work_id = re.sub(r'WS/\s*MP', 'WS/MP', work_id)
        return work_id
    return None

def extract_work_category_suffix(work_field: str, work_id: str = None) -> str:
    """Extract the standardized MPLADS category name embedded in the Work field.

    The Work field looks like:
        WS/MP18217/2024-2025/136141-Construction of roads, link roads, pathways ...
    The suffix after the work_id is the authoritative category string. It is a
    much more reliable signal than free-text keywords (e.g. a work whose category
    is 'Crematoriums...' is an ALLOWED category regardless of 'cremation' in the
    description).
    """
    if pd.isna(work_field):
        return ""
    work_str = str(work_field).strip()
    if work_id and not pd.isna(work_id):
        # strip the matched id prefix, then any leading separator
        wid = str(work_id)
        if wid in work_str:
            suffix = work_str.split(wid, 1)[1]
        else:
            return ""
    else:
        return ""
    suffix = re.sub(r'^[-_:\s]+', '', suffix)
    return suffix.strip()


def is_footer_row(row: pd.Series) -> bool:
    """Detect footer rows (Grand Total rows with garbled data)."""
    first_col = str(row.iloc[0]).strip().lower()
    if 'grand total' in first_col:
        return True
    non_null_count = row.notna().sum()
    if non_null_count <= 2:
        return True
    return False

def clean_text_field(val: str) -> str:
    """Clean text fields: handle garbled regional-language text, placeholder images."""
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('n/a', 'na', 'none', 'null', 'images', 'image'):
        return ""
    val_str = val_str.replace('\ufffd', ' ')
    val_str = re.sub(r'[?]{3,}', ' ', val_str)
    val_str = re.sub(r'\s+', ' ', val_str).strip()
    return val_str

def load_and_clean_csv(filepath: Path, name: str) -> Tuple[pd.DataFrame, Dict]:
    """Load a CSV, clean it, and return cleaned DataFrame + stats."""
    logger.info(f"Loading {name} from {filepath}")
    
    df = pd.read_csv(filepath, encoding='utf-8', low_memory=False)
    original_rows = len(df)
    
    footer_mask = df.apply(is_footer_row, axis=1)
    footer_count = footer_mask.sum()
    if footer_count > 0:
        logger.info(f"  Dropping {footer_count} footer row(s) from {name}")
        df = df[~footer_mask].copy()
    
    numeric_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ['amount', 'allocated', 'disbursed', 'consent', 'sanction', 'recommended', 'expenditure', 'fund']):
            if 'date' not in col_lower:
                numeric_cols.append(col)
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_indian_number)
    
    text_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ['description', 'work', 'category', 'state', 'ida', 'constituency', 'mp', 'parliament', 'vendor', 'calamity', 'name', 'status', 'image']):
            if col not in numeric_cols:
                text_cols.append(col)
    
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_text_field)
    
    if 'work_id' not in df.columns:
        work_col = None
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in ('work id', 'work_id'):
                work_col = col
                break
        if work_col is None:
            for col in df.columns:
                col_lower = col.lower().strip()
                if col_lower == 'work':
                    work_col = col
                    break
        if work_col:
            df['work_id'] = df[work_col].apply(extract_work_id)
            extracted_count = df['work_id'].notna().sum()
            logger.info(f"  Extracted work_id for {extracted_count}/{len(df)} rows in {name} (from column: {work_col})")
            if 'work_category_suffix' not in df.columns:
                df['work_category_suffix'] = df.apply(
                    lambda r: extract_work_category_suffix(r[work_col], r['work_id'])
                    if 'work_id' in df.columns else "",
                    axis=1
                )
                logger.info(f"  Extracted work_category_suffix for {df['work_category_suffix'].astype(bool).sum()}/{len(df)} rows in {name}")
    
    cleaned_rows = len(df)
    stats = {
        'original_rows': original_rows,
        'cleaned_rows': cleaned_rows,
        'footer_rows_dropped': int(footer_count),
        'work_ids_extracted': int(df['work_id'].notna().sum()) if 'work_id' in df.columns else 0
    }
    
    return df, stats

def find_col(df: pd.DataFrame, keywords: List[str]) -> str:
    """Find column matching any of the keywords (case-insensitive). Prefers exact matches."""
    cols_lower = {col.lower(): col for col in df.columns}
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in cols_lower:
            return cols_lower[kw_lower]
    for col in df.columns:
        col_lower = col.lower()
        if any(kw.lower() in col_lower for kw in keywords):
            return col
    return None

def join_lifecycle_tables(dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build master lifecycle table as a UNION of all work-bearing tables.

    Data reality (discovered Module 1): the source tables cover disjoint
    work_id sets (Sanctioned shares 0 ids with Recommended/Completed/
    Expenditure; Recommended/Completed/Expenditure form a connected graph).
    A sanctioned-anchored left join would leave ~all enrichment columns empty,
    so instead we union all work_ids and attach each table's columns.
    """
    logger.info("Building union master lifecycle table...")

    def pick(df, col_name):
        return find_col(df, [col_name]) or find_col(df, [col_name.split('_')[0]])

    frames = []
    for key in ['works_recommended', 'works_sanctioned', 'works_completed']:
        df = dataframes.get(key)
        if df is None or 'work_id' not in df.columns:
            continue
        keep = {'work_id'}
        rename = {}
        for col in df.columns:
            cl = col.lower()
            if cl in ('work_category_suffix',):
                rename[col] = 'work_category_suffix'
                keep.add(col)
            elif cl in ('work category',):
                rename[col] = 'work_category'
                keep.add(col)
            elif cl in ('work',):
                rename[col] = 'work_raw'
                keep.add(col)
            elif cl == 'ida':
                rename[col] = 'ida'
                keep.add(col)
            elif cl in ('state',):
                rename[col] = 'state'
                keep.add(col)
            elif 'parliament' in cl and 'mp' not in rename.values():
                rename[col] = 'mp_name'
                keep.add(col)
            elif cl in ('constituency',):
                rename[col] = 'constituency'
                keep.add(col)
            elif 'work description' in cl:
                rename[col] = 'work_description'
                keep.add(col)
            elif 'recommended date' in cl:
                rename[col] = 'recommended_date'
                keep.add(col)
            elif 'recommended amount' in cl:
                rename[col] = 'recommended_amount'
                keep.add(col)
            elif cl == 'sanction date':
                rename[col] = 'sanction_date'
                keep.add(col)
            elif 'sanction amount' in cl:
                rename[col] = 'sanction_amount'
                keep.add(col)
            elif 'work status' in cl:
                rename[col] = 'work_status'
                keep.add(col)
            elif 'completion date' in cl:
                rename[col] = 'completion_date'
                keep.add(col)
            elif 'amount disbursed' in cl:
                rename[col] = 'amount_disbursed'
                keep.add(col)
            elif cl in ('image',):
                rename[col] = 'image_url'
                keep.add(col)
        sub = df[[c for c in df.columns if c in keep]].copy()
        sub = sub.rename(columns={k: v for k, v in rename.items() if k in sub.columns})
        sub['source_table'] = key
        frames.append(sub)

    master = pd.concat(frames, ignore_index=True, sort=False)
    master = master.drop_duplicates(subset='work_id', keep='first')
    logger.info(f"Union master base: {master.shape}")

    # Patch item-level columns across tables by work_id (fill where missing)
    for col in ['work_category', 'work_category_suffix', 'work_raw', 'state', 'ida', 'mp_name', 'constituency',
                'work_description', 'recommended_date', 'recommended_amount',
                'sanction_date', 'sanction_amount', 'work_status', 'completion_date',
                'amount_disbursed', 'image_url']:
        if col in master.columns:
            # pull values from any table where present
            src = None
            for fr in frames:
                if col in fr.columns:
                    src = fr
                    break
            if src is not None and col in src.columns:
                m = src[['work_id', col]].dropna(subset=[col]).drop_duplicates('work_id')
                m = m.set_index('work_id')[col]
                master[col] = master[col].fillna(master['work_id'].map(m))

    # Aggregated expenditure joins (recommended+completed overlap with expenditure)
    expenditure = dataframes.get('expenditure')
    if expenditure is not None and 'work_id' in expenditure.columns:
        exp_amt_col = find_col(expenditure, ['Fund Disbursed', 'Disbursed Amount', 'Fund Disbursed Amount'])
        exp_vendor_col = find_col(expenditure, ['Vendor Name', 'Vendor'])
        exp_date_col = find_col(expenditure, ['Expenditure Date'])
        if exp_amt_col and exp_vendor_col:
            exp_agg = expenditure.groupby('work_id').agg(
                total_expenditure=(exp_amt_col, 'sum'),
                vendor_count=(exp_vendor_col, 'nunique'),
                vendors=(exp_vendor_col, lambda x: list(x.dropna().unique())),
                expenditure_count=(exp_vendor_col, 'count'),
            ).reset_index()
            if exp_date_col:
                exp_dates = expenditure.groupby('work_id')[exp_date_col].agg(
                    first_expenditure_date='min', last_expenditure_date='max'
                ).reset_index()
                exp_agg = exp_agg.merge(exp_dates, on='work_id', how='left')
            master = master.merge(exp_agg, on='work_id', how='left')

    # Allocated limit per MP+constituency
    allocated = dataframes.get('allocated_limit_1')
    if allocated is not None:
        mp_col = find_col(allocated, ["Hon'ble Members of Parliaments", "Hon'ble Members of Parliament", 'MP'])
        const_col = find_col(allocated, ['Constituency'])
        alloc_amt_col = find_col(allocated, ['Allocated AMOUNT', 'Allocated Amount'])
        if mp_col and const_col and alloc_amt_col:
            if 'mp_constituency_key' not in master.columns:
                master['mp_constituency_key'] = master['mp_name'].fillna('').astype(str) + '_' + master['constituency'].fillna('').astype(str)
            allocated['mp_constituency_key'] = allocated[mp_col].astype(str) + '_' + allocated[const_col].astype(str)
            alloc_df = allocated[['mp_constituency_key', alloc_amt_col]].drop_duplicates('mp_constituency_key')
            alloc_df = alloc_df.rename(columns={alloc_amt_col: 'allocated_amount'})
            master = master.merge(alloc_df, on='mp_constituency_key', how='left')
            master = master.drop(columns=['mp_constituency_key'])

    # Calamity consent per MP
    calamity = dataframes.get('calamity')
    if calamity is not None:
        mp_col = find_col(calamity, ["Hon'ble Members of Parliament", 'MP'])
        cal_amt_col = find_col(calamity, ['Consent Amount', 'Consent'])
        if mp_col and cal_amt_col:
            if 'mp_key' not in master.columns:
                master['mp_key'] = master['mp_name'].fillna('').astype(str)
            calamity['mp_key'] = calamity[mp_col].fillna('').astype(str)
            cal_agg = calamity.groupby('mp_key')[cal_amt_col].agg(
                total_calamity_consent='sum',
                calamity_events='count',
            ).reset_index()
            master = master.merge(cal_agg, on='mp_key', how='left')
            master = master.drop(columns=['mp_key'])

    logger.info(f"Master table shape: {master.shape}")
    return master

def run_module1() -> Tuple[pd.DataFrame, Dict]:
    """Run Module 1: Data ingestion + cleaning."""
    logger.info("=" * 60)
    logger.info("MODULE 1: Data Ingestion + Cleaning")
    logger.info("=" * 60)
    
    all_stats = {}
    dataframes = {}
    
    for key, filename in FILE_MAP.items():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue
        df, stats = load_and_clean_csv(filepath, key)
        dataframes[key] = df
        all_stats[key] = stats
        
    master = join_lifecycle_tables(dataframes)
    
    total_footer = sum(s.get('footer_rows_dropped', 0) for s in all_stats.values())
    total_original = sum(s.get('original_rows', 0) for s in all_stats.values())
    total_cleaned = sum(s.get('cleaned_rows', 0) for s in all_stats.values())
    total_work_ids = sum(s.get('work_ids_extracted', 0) for s in all_stats.values())
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Total original rows across all tables: {total_original}")
    logger.info(f"Total footer/malformed rows dropped: {total_footer}")
    logger.info(f"Total cleaned rows: {total_cleaned}")
    logger.info(f"Total work_ids extracted: {total_work_ids}")
    logger.info(f"Master lifecycle table shape: {master.shape}")
    logger.info(f"Master columns: {list(master.columns)}")
    
    return master, all_stats

if __name__ == "__main__":
    master_df, stats = run_module1()
    
    print("\n" + "=" * 80)
    print("MODULE 1 TEST RESULTS")
    print("=" * 80)
    print(f"\nMaster table shape: {master_df.shape}")
    print(f"\nColumns ({len(master_df.columns)}): {list(master_df.columns)}")
    
    print("\n--- Sample 10 joined rows ---")
    sample_cols = ['work_id', 'work_category', 'mp_name', 'State', 'IDA', 
                   'sanction_amount', 'recommended_amount', 'amount_disbursed',
                   'completion_date', 'work_status', 'total_expenditure', 'vendor_count']
    available_cols = [c for c in sample_cols if c in master_df.columns]
    print(master_df[available_cols].head(10).to_string())
    
    print("\n--- Data Quality Stats ---")
    for table, stat in stats.items():
        print(f"\n{table}:")
        for k, v in stat.items():
            print(f"  {k}: {v}")
    
    print(f"\nTotal footer/malformed rows dropped across all tables: {sum(s.get('footer_rows_dropped', 0) for s in stats.values())}")
    
    print("\n--- Work Status Distribution ---")
    if 'work_status' in master_df.columns:
        print(master_df['work_status'].value_counts().to_string())
    
    print("\n--- Work Category Distribution ---")
    if 'work_category' in master_df.columns:
        print(master_df['work_category'].value_counts().head(15).to_string())
    
    print("\n--- Missing work_id count ---")
    missing_work_id = master_df['work_id'].isna().sum()
    print(f"Rows without work_id: {missing_work_id}")