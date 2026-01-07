from __future__ import annotations

import pandas as pd

def conform_to_schema(df: pd.DataFrame, schema_cols: list[str]) -> pd.DataFrame:
    # add missing columns
    for c in schema_cols:
        if c not in df.columns:
            df[c] = None

    # order = schema first + extras last
    ordered = schema_cols + [c for c in df.columns if c not in schema_cols]
    return df[ordered]
