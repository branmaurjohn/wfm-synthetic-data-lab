from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

def build_profile(table: str, sample_csv: Path, out_json: Path):
    df = pd.read_csv(sample_csv, nrows=5)
    cols = list(df.columns)

    profile = {
        "table": table,
        "sample_csv": str(sample_csv).replace("\\", "/"),
        "columns": cols,
        "notes": "Generated from a real sample extract. Used to map synthetic fields to real UKG/DataHub column names."
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(f"Wrote profile: {out_json} ({len(cols)} columns)")

def main():
    base = Path("data/reference/samples")
    out = Path("profiles")

    build_profile("vTimecardTotal", base / "vTimecardTotal.sample.csv", out / "vTimecardTotal.profile.json")
    build_profile("vAccrualBalance", base / "vAccrualBalance.sample.csv", out / "vAccrualBalance.profile.json")
    build_profile("vDimBusinessStructure", base / "vDimBusinessStructure.sample.csv", out / "vDimBusinessStructure.profile.json")

if __name__ == "__main__":
    main()
