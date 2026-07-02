import pandas as pd
import numpy as np
import json
import re
from collections import Counter
from typing import Tuple, List, Dict, Any


SUPPORTED_EXTENSIONS = {
    '.csv': 'CSV',
    '.tsv': 'TSV',
    '.xlsx': 'Excel',
    '.xls': 'Excel (Legacy)',
    '.xlsm': 'Excel (Macro)',
    '.json': 'JSON',
    '.parquet': 'Parquet',
    '.ods': 'OpenDocument Spreadsheet',
}


def load_dataset(filepath):
    # type: (str) -> Tuple[pd.DataFrame, str]
    """
    Universally load a dataset from any supported format.
    Returns (dataframe, detected_format_name)
    """
    import os
    ext = os.path.splitext(filepath)[1].lower()

    df = None
    fmt = 'Unknown'

    # 1. Try to load based on extension
    try:
        if ext == '.csv':
            df = _load_csv(filepath)
            fmt = 'CSV'
        elif ext == '.tsv':
            df = pd.read_csv(filepath, sep='\t')
            fmt = 'TSV'
        elif ext in ('.xlsx', '.xlsm'):
            df = pd.read_excel(filepath, engine='openpyxl')
            fmt = f'Excel ({ext})'
        elif ext == '.xls':
            df = pd.read_excel(filepath, engine='xlrd')
            fmt = 'Excel (.xls)'
        elif ext == '.json':
            df = _load_json(filepath)
            fmt = 'JSON'
        elif ext == '.parquet':
            df = pd.read_parquet(filepath)
            fmt = 'Parquet'
        elif ext == '.ods':
            df = pd.read_excel(filepath, engine='odf')
            fmt = 'ODS'
    except Exception:
        pass  # We will try fallbacks

    if df is None:
        errors = []
        try:
            df = pd.read_excel(filepath, engine='openpyxl')
            fmt = 'Excel (Fallback)'
        except Exception as e1:
            errors.append(f"openpyxl error: {str(e1)}")
            try:
                df = pd.read_excel(filepath, engine='xlrd')
                fmt = 'Excel xlrd (Fallback)'
            except Exception as e1_xlrd:
                errors.append(f"xlrd error: {str(e1_xlrd)}")
                try:
                    df = _load_csv(filepath)
                    fmt = 'CSV (Fallback)'
                except Exception as e2:
                    errors.append(f"CSV error: {str(e2)}")
                    try:
                        df = _load_json(filepath)
                        fmt = 'JSON (Fallback)'
                    except Exception as e3:
                        errors.append(f"JSON error: {str(e3)}")
                        raise Exception(f"Failed to parse file as CSV, Excel, or JSON. Details: {' | '.join(errors)}")

    # Standardise column names
    df.columns = [str(c).strip() for c in df.columns]
    return df, fmt


def _load_csv(filepath: str) -> pd.DataFrame:
    """Auto-detect delimiter and encoding for CSV files."""
    import csv
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;|\t')
        sep = dialect.delimiter
    except csv.Error:
        sep = ','
    try:
        return pd.read_csv(filepath, sep=sep, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(filepath, sep=sep, low_memory=False, encoding='latin1')


def _load_json(filepath: str) -> pd.DataFrame:
    """Handle multiple JSON structures."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = json.load(f)
    if isinstance(raw, list):
        return pd.json_normalize(raw)
    elif isinstance(raw, dict):
        # Try to find the data key
        for key, val in raw.items():
            if isinstance(val, list) and len(val) > 0:
                return pd.json_normalize(val)
        return pd.json_normalize([raw])
    return pd.DataFrame()


def analyze_dataset(df: pd.DataFrame) -> dict:
    """
    Full schema-agnostic analysis. Works on any dataset regardless of columns.
    Returns a structured analysis dict.
    """
    total_rows, total_cols = df.shape
    total_cells = total_rows * total_cols

    columns_analysis = []
    all_issues = []
    type_issue_count = 0
    outlier_count = 0
    inconsistency_count = 0

    for col in df.columns:
        series = df[col]
        col_info = _analyze_column(series, col, total_rows)
        columns_analysis.append(col_info)
        all_issues.extend(col_info.get('issues', []))
        type_issue_count += col_info.get('type_issues', 0)
        outlier_count += col_info.get('outlier_count', 0)
        inconsistency_count += col_info.get('inconsistency_count', 0)

    # Aggregate
    total_missing = int(df.isnull().sum().sum())
    missing_pct = round(total_missing / total_cells * 100, 2) if total_cells else 0
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round(duplicate_rows / total_rows * 100, 2) if total_rows else 0
    empty_cols = [c['name'] for c in columns_analysis if c.get('is_empty')]
    constant_cols = [c['name'] for c in columns_analysis if c.get('is_constant')]

    return {
        'shape': {'rows': total_rows, 'cols': total_cols},
        'total_cells': total_cells,
        'missing': {'count': total_missing, 'pct': missing_pct},
        'duplicates': {'count': duplicate_rows, 'pct': duplicate_pct},
        'type_issues': type_issue_count,
        'outliers': outlier_count,
        'inconsistencies': inconsistency_count,
        'empty_columns': empty_cols,
        'constant_columns': constant_cols,
        'columns': columns_analysis,
        'all_issues': all_issues,
        'column_names': list(df.columns),
    }


def _analyze_column(series: pd.Series, col_name: str, total_rows: int) -> dict:
    issues = []
    missing = int(series.isnull().sum())
    missing_pct = round(missing / total_rows * 100, 2) if total_rows else 0
    unique_count = int(series.nunique())
    is_empty = missing == total_rows
    non_null = series.dropna()
    is_constant = unique_count == 1 and not is_empty

    # Detect dtype
    inferred_type = _infer_type(series)

    type_issues = 0
    outlier_count = 0
    inconsistency_count = 0

    if missing > 0:
        severity = 'high' if missing_pct > 30 else ('medium' if missing_pct > 10 else 'low')
        issues.append({
            'type': 'Missing Values',
            'column': col_name,
            'detail': f'{missing} missing ({missing_pct}%)',
            'severity': severity
        })

    if is_empty:
        issues.append({'type': 'Empty Column', 'column': col_name, 'detail': 'All values are null', 'severity': 'high'})

    if is_constant:
        issues.append({'type': 'Constant Column', 'column': col_name, 'detail': f'All values are "{non_null.iloc[0]}"', 'severity': 'medium'})

    # Numeric outliers
    if inferred_type == 'numeric':
        numeric_series = pd.to_numeric(series, errors='coerce').dropna()
        if len(numeric_series) > 10:
            q1, q3 = numeric_series.quantile(0.25), numeric_series.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers = numeric_series[(numeric_series < q1 - 1.5 * iqr) | (numeric_series > q3 + 1.5 * iqr)]
                outlier_count = len(outliers)
                if outlier_count > 0:
                    issues.append({
                        'type': 'Outliers',
                        'column': col_name,
                        'detail': f'{outlier_count} outlier(s) detected (IQR method)',
                        'severity': 'medium' if outlier_count < 10 else 'high'
                    })

    # Type mismatch issues
    if inferred_type == 'mixed':
        type_issues = 1
        issues.append({'type': 'Mixed Data Types', 'column': col_name, 'detail': 'Column contains mixed data types', 'severity': 'high'})

    # Inconsistency — categorical columns with format variations
    if inferred_type in ('text', 'categorical'):
        str_series = non_null.astype(str)
        variations = _detect_format_variations(str_series)
        if variations:
            inconsistency_count = 1
            issues.append({
                'type': 'Inconsistent Format',
                'column': col_name,
                'detail': f'Mixed formats detected: {", ".join(variations[:3])}',
                'severity': 'medium'
            })

    # Negative values in columns that look like they should be positive
    if inferred_type == 'numeric':
        num = pd.to_numeric(series, errors='coerce').dropna()
        neg_count = int((num < 0).sum())
        if neg_count > 0 and _col_should_be_positive(col_name):
            issues.append({'type': 'Negative Values', 'column': col_name, 'detail': f'{neg_count} unexpected negative value(s)', 'severity': 'medium'})

    # High cardinality warning for categorical
    if inferred_type in ('text', 'categorical') and unique_count == total_rows and total_rows > 10:
        issues.append({'type': 'High Cardinality', 'column': col_name, 'detail': 'Every value is unique — may be an ID column', 'severity': 'low'})

    return {
        'name': col_name,
        'dtype': str(series.dtype),
        'inferred_type': inferred_type,
        'missing': missing,
        'missing_pct': missing_pct,
        'unique_count': unique_count,
        'is_empty': is_empty,
        'is_constant': is_constant,
        'issues': issues,
        'type_issues': type_issues,
        'outlier_count': outlier_count,
        'inconsistency_count': inconsistency_count,
        'issue_count': len(issues),
    }


def _infer_type(series: pd.Series) -> str:
    non_null = series.dropna()
    if len(non_null) == 0:
        return 'empty'
    # Try numeric
    numeric = pd.to_numeric(non_null, errors='coerce')
    numeric_ratio = numeric.notna().sum() / len(non_null)
    if numeric_ratio > 0.9:
        return 'numeric'
    # Try datetime
    try:
        pd.to_datetime(non_null.head(50), errors='raise', infer_datetime_format=True)
        return 'datetime'
    except Exception:
        pass
    # Boolean check
    lower_vals = set(non_null.astype(str).str.lower().unique())
    if lower_vals.issubset({'true', 'false', '0', '1', 'yes', 'no'}):
        return 'boolean'
    # Mixed
    if 0.1 < numeric_ratio < 0.9:
        return 'mixed'
    # Cardinality for categorical vs text
    unique_ratio = series.nunique() / len(non_null)
    if unique_ratio < 0.3:
        return 'categorical'
    return 'text'


def _detect_format_variations(str_series: pd.Series) -> list:
    variations = []
    sample = str_series.head(500)
    lower_vals = set(sample.str.lower().unique())
    # Gender-like
    gender_variants = {'male', 'female', 'm', 'f', 'man', 'woman'}
    if len(lower_vals & gender_variants) > 1:
        variations.append('gender format (M/Male/male)')
    # Case inconsistency
    unique_vals = sample.unique()
    if len(unique_vals) > 1:
        lowered = [v.lower() for v in unique_vals if isinstance(v, str)]
        if len(set(lowered)) < len(unique_vals):
            variations.append('case inconsistency (e.g. "yes" vs "Yes")')
    # Leading/trailing whitespace
    if any(v != v.strip() for v in unique_vals if isinstance(v, str)):
        variations.append('leading/trailing whitespace')
    return variations


def _col_should_be_positive(col_name: str) -> bool:
    keywords = ['age', 'price', 'salary', 'cost', 'count', 'amount', 'qty', 'quantity', 'revenue', 'weight', 'height', 'score']
    return any(kw in col_name.lower() for kw in keywords)
