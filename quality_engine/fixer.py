import pandas as pd
import numpy as np
from typing import Tuple, List


def auto_fix(df, analysis, mode='safe'):
    # type: (pd.DataFrame, dict, str) -> Tuple[pd.DataFrame, List[str]]
    """
    Apply automatic fixes to a dataframe based on analysis results.
    Fully schema-agnostic.
    mode: 'safe' (preserves layout of unstructured reports) or 'strict' (fully cleans tables)
    Returns: (fixed_df, list_of_fixes_applied)
    """
    df_fixed = df.copy()
    fixes_applied = []

    # 1. Remove duplicate rows
    dup_count = analysis['duplicates']['count']
    if dup_count > 0:
        if mode == 'strict':
            before = len(df_fixed)
            df_fixed = df_fixed.drop_duplicates()
            after = len(df_fixed)
            fixes_applied.append(f"Removed {before - after} duplicate row(s)")
        else:
            fixes_applied.append(f"Ignored {dup_count} duplicate row(s) to preserve layout (Safe Mode)")

    # 2. Fix column-level issues
    for col_info in analysis['columns']:
        col = col_info['name']
        if col not in df_fixed.columns:
            continue

        inferred = col_info['inferred_type']
        missing = col_info['missing']

        # Empty columns
        if col_info.get('is_empty'):
            if mode == 'strict':
                df_fixed.drop(columns=[col], inplace=True)
                fixes_applied.append(f"Dropped empty column '{col}' (Strict Mode)")
            else:
                fixes_applied.append(f"Kept empty column '{col}' to preserve layout (Safe Mode)")
            continue

        # Constant columns
        if col_info.get('is_constant'):
            if mode == 'strict':
                df_fixed.drop(columns=[col], inplace=True)
                fixes_applied.append(f"Dropped constant column '{col}' (Strict Mode)")
            else:
                fixes_applied.append(f"Kept constant column '{col}' to preserve layout (Safe Mode)")
            continue

        # Fill missing values
        if missing > 0:
            if inferred == 'numeric':
                if mode == 'strict':
                    median_val = pd.to_numeric(df_fixed[col], errors='coerce').median()
                    df_fixed[col] = pd.to_numeric(df_fixed[col], errors='coerce').fillna(median_val)
                    fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with median ({round(median_val, 4)}) (Strict Mode)")
                else:
                    fixes_applied.append(f"Left {missing} missing value(s) in '{col}' as blank (Safe Mode)")
            elif inferred in ('text', 'categorical', 'boolean'):
                if mode == 'strict':
                    mode_val = df_fixed[col].mode()
                    if len(mode_val) > 0:
                        df_fixed[col] = df_fixed[col].fillna(mode_val[0])
                        fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with mode ('{mode_val[0]}') (Strict Mode)")
                    else:
                        df_fixed[col] = df_fixed[col].fillna('Unknown')
                        fixes_applied.append(f"Filled {missing} missing value(s) in '{col}' with 'Unknown' (Strict Mode)")
                else:
                    fixes_applied.append(f"Left {missing} missing string value(s) in '{col}' as blank (Safe Mode)")
            elif inferred == 'datetime':
                if mode == 'strict':
                    df_fixed[col] = df_fixed[col].ffill().bfill()
                    fixes_applied.append(f"Forward/backward filled {missing} missing datetime(s) in '{col}' (Strict Mode)")
                else:
                    fixes_applied.append(f"Left {missing} missing datetime(s) in '{col}' as blank (Safe Mode)")

        # Fix leading/trailing whitespace for string columns (this is always safe)
        if inferred in ('text', 'categorical'):
            df_fixed[col] = df_fixed[col].astype(str).str.strip()
            df_fixed[col] = df_fixed[col].replace('nan', np.nan)

        # Standardise case for low-cardinality categorical columns (this is always safe)
        if inferred == 'categorical':
            unique_vals = df_fixed[col].dropna().unique()
            if len(unique_vals) > 0 and len(unique_vals) < 20:
                lower_map = {}
                for v in unique_vals:
                    lower_map[v] = str(v).strip().title()
                df_fixed[col] = df_fixed[col].map(lower_map).fillna(df_fixed[col])

    # 3. Reset index
    df_fixed = df_fixed.reset_index(drop=True)

    return df_fixed, fixes_applied
