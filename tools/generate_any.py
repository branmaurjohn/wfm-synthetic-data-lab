from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path when running `python tools/generate_any.py ...`
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wfm_synth.config import load_config
from wfm_synth.schema_registry import snapshot_path_for_table, load_snapshot
from wfm_synth.generate_timecard_total import generate_vtimecardtotal
from wfm_synth.generate_accrual_balance import generate_vaccrualbalance
from wfm_synth.generate_dim_business_structure import generate_vdimbusinessstructure

def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: python tools/generate_any.py <scenario_yaml> <table_name> <out_dir>")

    scenario = Path(sys.argv[1]).resolve()
    table = sys.argv[2]
    out_dir = Path(sys.argv[3]).resolve()

    cfg = load_config(str(scenario))
    snap_path = snapshot_path_for_table(table)
    snap = load_snapshot(snap_path)

    if snap.table != table:
        raise SystemExit(f"Snapshot table mismatch: expected {table}, got {snap.table}")

    schema_cols = snap.column_names

    if table == "vTimecardTotal":
        out = generate_vtimecardtotal(cfg, {"table": snap.table, "unique_identifier": snap.unique_identifier, "columns": snap.columns}, out_dir)
    elif table == "vAccrualBalance":
        out = generate_vaccrualbalance(cfg, schema_cols, out_dir)
    elif table == "vDimBusinessStructure":
        out = generate_vdimbusinessstructure(cfg, schema_cols, out_dir)
    else:
        raise SystemExit(f"No generator registered for table: {table}")

    print(f"Wrote: {out}")
    print(f"Metadata: {out_dir / 'run_metadata.json'}")

if __name__ == "__main__":
    main()
