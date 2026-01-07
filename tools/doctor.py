from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def main() -> None:
    print(f"Repo root: {REPO_ROOT}")
    needed = [
        REPO_ROOT / "schemas" / "snapshots" / "vTimecardTotal.schema.json",
        REPO_ROOT / "schemas" / "snapshots" / "vAccrualBalance.schema.json",
        REPO_ROOT / "schemas" / "snapshots" / "vDimBusinessStructure.schema.json",
        REPO_ROOT / "scenarios" / "baptist_south_fl.yaml",
        REPO_ROOT / "profiles" / "vTimecardTotal.profile.json",
    ]

    missing = [p for p in needed if not p.exists()]
    if missing:
        print("MISSING FILES:")
        for p in missing:
            print(f"  - {p}")
        raise SystemExit(2)

    try:
        import faker  # noqa
        import pandas  # noqa
        import yaml  # noqa
        import openpyxl  # noqa
    except Exception as e:
        print("Python dependency problem:", repr(e))
        raise SystemExit(3)

    print("OK: files exist + key dependencies import clean")

if __name__ == "__main__":
    main()
