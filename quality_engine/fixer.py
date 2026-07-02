import pandas as pd
import numpy as np
from typing import Tuple, List


def auto_fix(df, analysis):
    # type: (pd.DataFrame, dict) -> Tuple[pd.DataFrame, List[str]]
    """
    Apply automatic fixes to a dataframe based on analysis results.
    Fully schema-agnostic.
    Returns: (fixed_df, list_of_fixes_applied)
    """
    df_fixed = df.copy()
    fixes_applied = []

    # 1. Remove duplicate rows
    dup_count = analysis['duplicates']['count']
    if dup_count > 0:
        before = len(df_fixed)
        df_fixed = df_fixed.drop_duplicates()
        after = len(df_fixed)
        fixes_applied.append(f"Removed {before - after} duplicate row(s)")

    # 2. Fix column-level issues
    for col_info in analysis['columns']:
        col = col_info['name']
        if col not in df_fixed.columns:
            continue

        inferred = col_info['inferred_type']
        missing = col_info['missing']

        # Skip empty columns (all null) — just drop them
        if col_info.get('is_empty'):
            df_fixed.drop(columns=[col], inplace=True)
            fixes_applied.append(f"Dropped empty column '{col}'")
            continue

        # Skip constant columns
        if col_info.get('is_constant'):
            df_fixed.drop(columns=[col], inplace=True)
            fixes_applied.append(f"Dropped constant column '{col}'")
            continue

        # Fill missing values
        if missing > 0:
            if inferred == 'numeric':
                median_val = pd.to_numeric(df_fixed[col], errors='coerce').median()
                df_fixed[col] = pd.to_numeric(df_fixed[col], errors='coerce').fillna(median_val)
                fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with median ({round(median_val, 4)})")
            elif inferred in ('text', 'categorical', 'boolean'):
                mode_val = df_fixed[col].mode()
                if len(mode_val) > 0:
                    df_fixed[col] = df_fixed[col].fillna(mode_val[0])
                    fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with mode ('{mode_val[0]}')")
                else:
                    df_fixed[col] = df_fixed[col].fillna('Unknown')
                    fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with 'Unknown'")
            elif inferred == 'datetime':
                df_fixed[col] = df_fixed[col].ffill().bfill()
                fixes_applied.append(f"Forward/backward filled {missing} missing datetime(s) in '{col}'")

        # Fix leading/trailing whitespace for string columns
        if inferred in ('text', 'categorical'):
            df_fixed[col] = df_fixed[col].astype(str).str.strip()

        # Standardise case for low-cardinality categorical columns
        if inferred == 'categorical':
            unique_vals = df_fixed[col].dropna().unique()
            lower_map = {}
            for v in unique_vals:
                lower_map[v] = str(v).strip().title()
            df_fixed[col] = df_fixed[col].map(lower_map).fillna(df_fixed[col])

    # 3. Reset index
    df_fixed = df_fixed.reset_index(drop=True)

    return df_fixed, fixes_applied
