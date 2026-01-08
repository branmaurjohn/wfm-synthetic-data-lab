$ErrorActionPreference = "Stop"

wfm-synth generate-pack scenarios/tiny_hospital_smoke.yaml --out-base .
$PackPath = Get-ChildItem -Path packs\tiny_hospital_smoke | Sort-Object LastWriteTime -Descending | Select-Object -First 1

wfm-synth validate-pack $PackPath.FullName
