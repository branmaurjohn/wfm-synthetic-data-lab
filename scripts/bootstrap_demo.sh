#!/usr/bin/env bash
set -euo pipefail

SCENARIO_PATH=${1:-"scenarios/tiny_hospital_smoke.yaml"}
PACK_ROOT="packs"
LATEST_LINK="$PACK_ROOT/latest"

if [ -d "../wfm-synthetic-data-lab/packs/latest" ]; then
  echo "Using external pack: ../wfm-synthetic-data-lab/packs/latest"
  PACK_PATH="../wfm-synthetic-data-lab/packs/latest"
else
  if [ -d "$LATEST_LINK" ]; then
    echo "Using local pack: $LATEST_LINK"
    PACK_PATH="$LATEST_LINK"
  else
    echo "Generating SPC pack from $SCENARIO_PATH"
    PACK_PATH=$(wfm-synth generate-pack "$SCENARIO_PATH" --out-base . | awk '{print $3}')
    mkdir -p "$PACK_ROOT"
    ln -sfn "$PACK_PATH" "$LATEST_LINK"
  fi
fi

echo "Validating pack: $PACK_PATH"
wfm-synth validate-pack "$PACK_PATH"

mkdir -p outputs
cat > outputs/demo_summary.md <<SUMMARY
# Demo Summary

- Scenario: $(basename "$(dirname "$PACK_PATH")")
- Run ID: $(basename "$PACK_PATH")
- Pack Path: $PACK_PATH
- Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

This demo validates the Synthetic Pack Contract (SPC) and demonstrates repeatable
local pack generation for downstream analytics.
SUMMARY

cat > outputs/demo_log.json <<LOG
{
  "repo_name": "wfm-synthetic-data-lab",
  "demo_version": "$(git rev-parse HEAD)",
  "spc_version": "1.0.0",
  "schema_version": "v1.1",
  "scenario": "tiny_hospital_smoke",
  "run_id": "$(basename "$PACK_PATH")",
  "tables_consumed": ["employee", "org_unit", "schedule", "timecard", "pay_code", "labor_daily"],
  "status": "SUCCESS",
  "runtime_seconds": 0
}
LOG

cat > outputs/demo_dashboard.html <<HTML
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>WFM Synthetic Pack Health Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; }
    pre { background: #f5f5f5; padding: 16px; }
  </style>
</head>
<body>
  <h1>WFM Synthetic Pack Health Report</h1>
  <p>Pack: $PACK_PATH</p>
  <pre>$(cat "$PACK_PATH/checks/health_report.md")</pre>
</body>
</html>
HTML
