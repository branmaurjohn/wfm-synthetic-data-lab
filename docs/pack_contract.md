# Synthetic Pack Contract (SPC)

## Purpose
The Synthetic Pack Contract (SPC) defines how every synthetic data pack is structured, named, and validated. It is the single canonical contract for this ecosystem. Downstream repos must validate packs against this contract and must not redefine it.

## Canonical pack layout
Every pack **must** use the following structure:

```
packs/<scenario>/<run_id>/
  pack_manifest.json
  tables/
    <table>.csv | <table>.parquet
  metadata/
    <table>.json
  checks/
    health_report.json (optional, validated if present)
    health_report.md   (optional, human view)
```

### Required files
- `pack_manifest.json`
- `tables/<table>.csv` or `tables/<table>.parquet`
- `metadata/<table>.json`

### Optional files
- `checks/health_report.json`
- `checks/health_report.md`

## Manifest rules
The manifest **must** validate against `spc_schema.json`. It includes:

- Contract versions (`spc_version`, `schema_version`, `metrics_version`)
- Scenario metadata (`scenario`, `run_id`, `seed`, `time_window`)
- Tables and grains
- Primary key mapping (`key_map`)
- Generation stats and row counts

## SemVer policy
`spc_version` follows SemVer:

- **Patch**: doc or validation fixes only
- **Minor**: additive, backward-compatible fields
- **Major**: breaking changes (renames, grain changes, removed fields)

Downstream repos pin compatibility in `config/spc_compat.yaml` (e.g., `spc_version: "1.0.x"`).

## Validation CLI
Use the built-in validator to enforce the contract:

```
wfm-synth validate-pack /path/to/pack
```

Validation checks:
- Folder structure
- Required files are present
- `pack_manifest.json` validates against `spc_schema.json`
- Optional health report (if present) validates required keys

## Health checks
Every run should emit a `checks/health_report.json` with at least:

- FK coverage (orphan counts)
- Time window sanity (out-of-range dates)
- Ratio sanity (OT%, weekend%, callout% vs scenario bounds)

A human-readable `checks/health_report.md` is recommended for quick review.
