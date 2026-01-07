from __future__ import annotations
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when running `python tools/generate.py ...`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wfm_synth.config import load_config
from wfm_synth.generate_timecard_total import load_schema_snapshot, generate_vtimecardtotal

def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python tools/generate.py <scenario_yaml> <schema_json> <out_dir>")

    scenario = Path(sys.argv[1]).resolve()
    schema = Path(sys.argv[2]).resolve()
    out_dir = Path(sys.argv[3]).resolve()

    cfg = load_config(str(scenario))
    sch = load_schema_snapshot(schema)

    table = sch.get("table")
    if table != "vTimecardTotal":
        raise SystemExit(f"Schema table is {table}, expected vTimecardTotal")

    out_path = generate_vtimecardtotal(cfg, sch, out_dir)
    print(f"Wrote: {out_path}")
    print(f"Metadata: {out_dir / 'run_metadata.json'}")

if __name__ == "__main__":
    main()
