from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SchemaSnapshot:
    table: str
    unique_identifier: str | None
    columns: list[dict]

    @property
    def column_names(self) -> list[str]:
        return [c["name"] for c in self.columns]

def load_snapshot(path: Path) -> SchemaSnapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SchemaSnapshot(
        table=raw.get("table"),
        unique_identifier=raw.get("unique_identifier"),
        columns=raw.get("columns") or [],
    )

def snapshot_path_for_table(table: str, snapshots_dir: Path | None = None) -> Path:
    snapshots_dir = snapshots_dir or Path("schemas/snapshots")
    p = snapshots_dir / f"{table}.schema.json"
    if not p.exists():
        raise FileNotFoundError(f"Schema snapshot not found: {p}")
    return p
