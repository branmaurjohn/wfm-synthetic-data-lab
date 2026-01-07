from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd

@dataclass
class BusinessStructureIndex:
    df: pd.DataFrame

    @staticmethod
    def load(csv_path: Path) -> "BusinessStructureIndex":
        df = pd.read_csv(csv_path)

        # Normalize common columns if present
        for c in df.columns:
            if isinstance(c, str):
                df.rename(columns={c: c.strip()}, inplace=True)

        return BusinessStructureIndex(df=df)

    def find_facility_candidates(self, facility_code_4: str) -> pd.DataFrame:
        # We don't know exact column names in your export - so we search broadly.
        fc = str(facility_code_4).zfill(4)

        hits = []
        for col in self.df.columns:
            s = self.df[col].astype(str)
            m = s.str.contains(fc, na=False)
            if m.any():
                tmp = self.df.loc[m].copy()
                tmp["_match_col"] = col
                hits.append(tmp)

        if not hits:
            return self.df.head(0)

        out = pd.concat(hits, ignore_index=True)
        return out

def extract_facility_unit_codes(org_path: str) -> tuple[str, str]:
    """
    From: AHS/OK/OK/SOUTH 5265/CC/Intensive Care Unit - 1004/RN
    Extracts facility_code=5265, unit_code=1004
    """
    s = str(org_path)

    # facility_code: last 4 digits in "SOUTH 5265" chunk
    facility_code = None
    unit_code = None

    # crude but robust patterns
    import re

    m1 = re.search(r"\b(\d{4})\b", s)
    if m1:
        facility_code = m1.group(1)

    m2 = re.search(r"-\s*(\d{4})\b", s)
    if m2:
        unit_code = m2.group(1)

    return (facility_code or "0000", unit_code or "0000")
