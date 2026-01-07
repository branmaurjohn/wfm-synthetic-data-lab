from __future__ import annotations
from datetime import date, datetime
import random
import re

def coerce(dtype: str, value, r: random.Random):
    if value is None:
        return None

    d = (dtype or "").lower()

    # normalize dictionary dtype variants
    if "int" in d:
        try:
            return int(float(value))
        except Exception:
            return int(r.randint(0, 1000))

    if "float" in d or "double" in d or "decimal" in d or "numeric" in d:
        try:
            return float(value)
        except Exception:
            return round(r.uniform(0, 100), 2)

    if "bool" in d:
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        return s in ("1", "true", "t", "y", "yes")

    if "date" in d and "time" not in d:
        if isinstance(value, date):
            return value.isoformat()
        return str(value)[:10]

    if "time" in d or "timestamp" in d or "datetime" in d:
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        s = str(value)
        # try to keep ISO-ish
        return s.replace(" ", "T")

    # default string
    return str(value)
