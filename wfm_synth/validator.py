from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from jsonschema import ValidationError, validate


def _load_schema(schema_path: Path) -> Dict[str, object]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validate_health_report(report_path: Path) -> List[str]:
    errors: List[str] = []
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if "summary" not in payload or "checks" not in payload:
        errors.append("health_report.json missing required keys: summary/checks")
        return errors
    summary = payload["summary"]
    for key in ["ERROR", "WARN", "INFO"]:
        if key not in summary:
            errors.append(f"health_report.json summary missing {key}")
    if not isinstance(payload["checks"], list):
        errors.append("health_report.json checks must be a list")
    return errors


def validate_pack(pack_path: Path, schema_path: Path) -> List[str]:
    errors: List[str] = []
    pack_path = pack_path.resolve()

    manifest_path = pack_path / "pack_manifest.json"
    tables_dir = pack_path / "tables"
    metadata_dir = pack_path / "metadata"

    if not manifest_path.exists():
        errors.append("Missing pack_manifest.json")
        return errors

    if not tables_dir.exists():
        errors.append("Missing tables/ directory")
    if not metadata_dir.exists():
        errors.append("Missing metadata/ directory")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = _load_schema(schema_path)

    try:
        validate(instance=manifest, schema=schema)
    except ValidationError as exc:
        errors.append(f"Manifest validation error: {exc.message}")

    tables = manifest.get("tables", [])
    for table in tables:
        csv_path = tables_dir / f"{table}.csv"
        parquet_path = tables_dir / f"{table}.parquet"
        if not csv_path.exists() and not parquet_path.exists():
            errors.append(f"Missing table file for {table}")
        meta_path = metadata_dir / f"{table}.json"
        if not meta_path.exists():
            errors.append(f"Missing metadata file for {table}")

    checks_dir = pack_path / "checks"
    health_report = checks_dir / "health_report.json"
    if health_report.exists():
        errors.extend(_validate_health_report(health_report))

    if "packs" not in pack_path.parts:
        errors.append("Pack path does not include 'packs' in directory tree")

    return errors
