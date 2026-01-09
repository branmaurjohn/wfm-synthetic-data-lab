$ErrorActionPreference = "Stop"

$ScenarioPath = if ($args.Count -gt 0) { $args[0] } else { "scenarios/tiny_hospital_smoke.yaml" }
$PackRoot = "packs"
$LatestLink = Join-Path $PackRoot "latest"

if (Test-Path "..\wfm-synthetic-data-lab\packs\latest") {
  Write-Host "Using external pack: ..\wfm-synthetic-data-lab\packs\latest"
  $PackPath = "..\wfm-synthetic-data-lab\packs\latest"
} elseif (Test-Path $LatestLink) {
  Write-Host "Using local pack: $LatestLink"
  $PackPath = $LatestLink
} else {
  Write-Host "Generating SPC pack from $ScenarioPath"
  $PackPath = (wfm-synth generate-pack $ScenarioPath --out-base . | Select-Object -Last 1).Split(" ")[-1]
  New-Item -ItemType Directory -Force -Path $PackRoot | Out-Null
  if (Test-Path $LatestLink) { Remove-Item $LatestLink -Force }
  New-Item -ItemType SymbolicLink -Path $LatestLink -Target $PackPath | Out-Null
}

Write-Host "Validating pack: $PackPath"
wfm-synth validate-pack $PackPath

New-Item -ItemType Directory -Force -Path outputs | Out-Null
@"
# Demo Summary

- Scenario: $(Split-Path (Split-Path $PackPath -Parent) -Leaf)
- Run ID: $(Split-Path $PackPath -Leaf)
- Pack Path: $PackPath
- Generated: $(Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ")

This demo validates the Synthetic Pack Contract (SPC) and demonstrates repeatable
local pack generation for downstream analytics.
"@ | Set-Content outputs/demo_summary.md

@"
{
  "repo_name": "wfm-synthetic-data-lab",
  "demo_version": "$(git rev-parse HEAD)",
  "spc_version": "1.0.0",
  "schema_version": "v1.1",
  "scenario": "tiny_hospital_smoke",
  "run_id": "$(Split-Path $PackPath -Leaf)",
  "tables_consumed": ["employee", "org_unit", "schedule", "timecard", "pay_code", "labor_daily"],
  "status": "SUCCESS",
  "runtime_seconds": 0
}
"@ | Set-Content outputs/demo_log.json

$healthReport = Get-Content "$PackPath\checks\health_report.md" -Raw
@"
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
  <p>Pack: $PackPath</p>
  <pre>$healthReport</pre>
</body>
</html>
"@ | Set-Content outputs/demo_dashboard.html
