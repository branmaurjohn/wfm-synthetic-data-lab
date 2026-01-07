from __future__ import annotations
from datetime import datetime, date, timedelta
import random
import string

from wfm_synth.typed_values import coerce

def dtype_map_from_snapshot(snapshot_columns: list[dict]) -> dict[str, str]:
    return {c.get("name"): (c.get("dtype") or "") for c in snapshot_columns}

def random_string(r: random.Random, n: int = 10) -> str:
    alpha = string.ascii_letters + string.digits
    return "".join(r.choice(alpha) for _ in range(n))

def fill_value_for_dtype(dtype: str, r: random.Random):
    d = (dtype or "").lower()
    if "int" in d:
        return int(r.randint(0, 10_000))
    if "float" in d or "double" in d or "decimal" in d or "numeric" in d:
        return round(r.uniform(0, 500), 2)
    if "bool" in d:
        return bool(r.randint(0, 1))
    if "date" in d and "time" not in d:
        # within last 2 years
        dd = date.today() - timedelta(days=r.randint(0, 730))
        return dd.isoformat()
    if "time" in d or "timestamp" in d or "datetime" in d:
        dt = datetime.utcnow() - timedelta(days=r.randint(0, 730), minutes=r.randint(0, 1440))
        return dt.isoformat(timespec="seconds")
    # default string
    return random_string(r, 12)

def fill_missing_columns(row: dict, target_cols: list[str], schema_dtypes: dict[str, str], r: random.Random) -> dict:
    """
    Ensure every target column exists. If missing, fill with plausible data based on dtype if known.
    """
    out = dict(row)
    for c in target_cols:
        if c in out:
            # coerce to dtype if we know it
            dt = schema_dtypes.get(c, "")
            out[c] = coerce(dt, out[c], r)
        else:
            dt = schema_dtypes.get(c, "")
            out[c] = coerce(dt, fill_value_for_dtype(dt, r), r)
    return out
