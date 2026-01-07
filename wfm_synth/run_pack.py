from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Tuple

from wfm_synth.config import GeneratorConfig
from wfm_synth.schema_registry import load_snapshot, snapshot_path_for_table
from wfm_synth.profiles import load_profile
from wfm_synth.column_mapper import build_mapping

from wfm_synth.generate_timecard_total import generate_vtimecardtotal
from wfm_synth.generate_accrual_balance import generate_vaccrualbalance
from wfm_synth.generate_dim_business_structure import generate_vdimbusinessstructure

from wfm_synth.registry import get_table_specs


def _toposort_tables(requested: List[str]) -> List[str]:
    specs = get_table_specs()

    # Expand dependencies
    expanded = set()
    visiting = set()

    def visit(t: str):
        if t in expanded:
            return
        if t in visiting:
            raise RuntimeError(f"Dependency cycle detected at {t}")
        if t not in specs:
            raise RuntimeError(f"Table not registered: {t}")
        visiting.add(t)
        for dep in specs[t].depends_on:
            visit(dep)
        visiting.remove(t)
        expanded.add(t)

    for t in requested:
        visit(t)

    # Now produce ordered list respecting deps
    ordered: List[str] = []
    temp = set()

    def emit(t: str):
        if t in ordered:
            return
        if t in temp:
            raise RuntimeError(f"Dependency cycle detected at {t}")
        temp.add(t)
        for dep in specs[t].depends_on:
            emit(dep)
        temp.remove(t)
        if t in expanded:
            ordered.append(t)

    for t in requested:
        emit(t)

    return ordered


def run_pack(
    cfg: GeneratorConfig,
    out_base: Path,
    tables: Optional[List[str]] = None,
) -> Path:
    """
    Generate a multi-table dataset pack into:
      out_base/<table>/<table>.csv
      out_base/<table>/run_metadata.json
    plus:
      out_base/run_manifest.json

    Returns path to run_manifest.json
    """
    out_base = out_base.resolve()
    out_base.mkdir(parents=True, exist_ok=True)

    specs = get_table_specs()
    if not tables:
        tables = list(specs.keys())

    ordered = _toposort_tables(tables)

    started = time.time()
    run_id = f"{cfg.run_name}-{int(started)}"

    manifest = {
        "run_id": run_id,
        "run_name": cfg.run_name,
        "seed_mode": cfg.seed_mode,
        "seed": cfg.seed,
        "facility": asdict(cfg.facility) if cfg.facility else None,
        "population": asdict(cfg.population) if cfg.population else None,
        "window": asdict(cfg.window) if cfg.window else None,
        "tables_requested": tables,
        "tables_generated": [],
        "outputs": [],
        "created_at_unix": int(started),
    }

    for table in ordered:
        table_dir = out_base / table
        table_dir.mkdir(parents=True, exist_ok=True)

        snap_path = snapshot_path_for_table(table)
        snap = load_snapshot(snap_path)

        # Optional profile-driven ordering + mapping
        profile_cols = None
        mapping = None
        try:
            profile = load_profile(table)
            profile_cols = profile.columns
            mapping = build_mapping(profile_cols)
        except Exception:
            profile_cols = None
            mapping = None

        if table == "vDimBusinessStructure":
            out_csv = generate_vdimbusinessstructure(
                cfg,
                snap.column_names,
                table_dir,
                profile_cols,
                mapping,
            )
        elif table == "vTimecardTotal":
            out_csv = generate_vtimecardtotal(
                cfg,
                {"table": snap.table, "unique_identifier": snap.unique_identifier, "columns": snap.columns},
                table_dir,
                profile_cols,
                mapping,
            )
        elif table == "vAccrualBalance":
            out_csv = generate_vaccrualbalance(
                cfg,
                snap.column_names,
                table_dir,
                profile_cols,
                mapping,
            )
        else:
            raise RuntimeError(f"No generator implemented for: {table}")

        manifest["tables_generated"].append(table)
        manifest["outputs"].append(
            {
                "table": table,
                "csv": str(Path(out_csv).resolve()),
                "metadata": str((table_dir / "run_metadata.json").resolve()),
            }
        )

    manifest_path = out_base / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest_path
