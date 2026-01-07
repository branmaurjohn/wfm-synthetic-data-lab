from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ColumnProfile:
    table: str
    columns: list[str]

def load_profile(table: str, profiles_dir: Path | None = None) -> ColumnProfile:
    profiles_dir = profiles_dir or Path("profiles")
    p = profiles_dir / f"{table}.profile.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return ColumnProfile(table=raw["table"], columns=raw["columns"])
