# WFM-Synthetic-Data-Lab ⚡️

[![DATA: SYNTHETIC ONLY](https://img.shields.io/badge/DATA-SYNTHETIC%20ONLY-red)](#synthetic-safety) [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#quickstart) [![CLI](https://img.shields.io/badge/CLI-wfm--synth-black)](#cli) [![UKG Pro WFM](https://img.shields.io/badge/UKG-Pro%20WFM%20%2F%20DataHub-6f2dbd)](#why-this-exists)

> **This repo is the power plant.**\
> It generates *table-accurate*, *schema-driven*, *join-safe* synthetic UKG Pro WFM / DataHub-style datasets so every other repo in the portfolio can run **without** access to real enterprise data.

If you’re looking for the “how the hell did he do that?” moment: this is it.\
Every visitor gets a fresh dataset experience (random seed mode) unless you explicitly lock it to deterministic (fixed seed).

------------------------------------------------------------------------

## Why this exists

Most demo repos die because the data is fake in an obvious way:
- same rows every run
- missing key columns
- no joinability
- no believable WFM behavior

This generator solves that by:
- extracting **schemas from the Omni Data Dictionary** (XLSX → snapshot JSON)
- generating **table-accurate CSVs** with realistic distributions
- producing output packs with **manifest + metadata** so pipelines & BI can plug in immediately

---

## What success looks like

When you run a pack:
- `vTimecardTotal.csv` is **non-empty**, **schema-aligned**, and **joinable** to business structure
- core keys aren’t null (ex: `costCenterId`, `payCode`, `partitionDate`)
- output is different every run unless you lock the seed

---

## Quickstart (Windows)

### 1) Install (editable)
```bat
cd /d C:\Temp\wfm-synthetic-data-lab
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
```
### 2) Repo health check
```
wfm-synth doctor
```
### 3) Generate a demo pack (3 tables)
```
rmdir /s /q output\baptist_south_fl
wfm-synth run scenarios\baptist_south_fl.yaml output\baptist_south_fl --tables vDimBusinessStructure,vTimecardTotal,vAccrualBalance
```
Expected result:

- output\baptist_south_fl\run_manifest.json
- one folder per table with *.csv + run_metadata.json
---
## SPC packs (contract-first demo)

This repo ships a canonical **Synthetic Pack Contract (SPC)** and a tiny demo scenario to generate SPC-compliant packs.

### Generate a tiny SPC pack
```
wfm-synth generate-pack scenarios\\tiny_hospital_smoke.yaml --out-base .
```

### Validate a pack
```
wfm-synth validate-pack packs\\tiny_hospital_smoke\\<run_id>
```

### One-button demo
```
scripts\\bootstrap_demo.ps1
```

This produces:
- `outputs/demo_summary.md`
- `outputs/demo_dashboard.html`
- `outputs/demo_log.json`

See `docs/pack_contract.md` for the full SPC definition.

---
## Validate the output (fast checks)

### Null-rate check for key columns (vTimecardTotal)
```
python -c "import pandas as pd; p=r'output\baptist_south_fl\vTimecardTotal\vTimecardTotal.csv'; df=pd.read_csv(p,dtype=str); print('shape',df.shape); print('costCenterId_null_pct', (df['costCenterId'].isna().mean()*100)); print('payCode_null_pct', (df['payCode'].isna().mean()*100)); print('partitionDate_null_pct', (df['partitionDate'].isna().mean()*100));"
```
### Join coverage check: Timecard → BusinessStructure (UNIT)
```
python -c "import pandas as pd; t=pd.read_csv(r'output\baptist_south_fl\vTimecardTotal\vTimecardTotal.csv',dtype=str); b=pd.read_csv(r'output\baptist_south_fl\vDimBusinessStructure\vDimBusinessStructure.csv',dtype=str); t=t.dropna(subset=['facility_code','unit_code']); b=b[b['level'].eq('UNIT')].dropna(subset=['facility_code','unit_code','costCenter']); t['k']=t['facility_code'].str.zfill(4)+t['unit_code'].str.zfill(4); b['k']=b['facility_code'].str.zfill(4)+b['unit_code'].str.zfill(4); m=t[['k','org_path']].merge(b[['k','nodePath','costCenter']],on='k',how='left'); ok=m['nodePath'].notna().mean()*100; print('rows_checked=%s join_coverage_pct=%.2f%%'%(len(m),ok));"
```
---

## Architecture
```
flowchart LR
  A[Omni Data Dictionary XLSX] --> B[Schema Snapshot JSON]
  B --> C[Schema Utilities + DType Fillers]
  D[Scenario YAML] --> E[Generator Engine]
  C --> E
  E --> F[Output Pack: CSV + metadata + manifest]
  F --> G[Downstream Repos: BI / SQL / ML / Pipelines]
```
---

## Repo Layout
```
schemas/
  snapshots/                # Table schema snapshots (JSON)
profiles/                   # Optional profile hints / mapping
scenarios/                  # Scenario YAMLs (facility + units + population + window)
tools/                      # Schema/profile helpers
wfm_synth/                  # Engine + generators + CLI
data/reference/             # safe reference inputs / samples (non-prod)
output/                     # generated packs (gitignored)
```
---

## Scenarios (how you describe “a world”)

Scenario YAML controls:
- Facility identity: company/state/market/facility/service line
- Units: unit_code + job + weights
- Population: headcount + promotion/attrition/termination rates (0–0.90)
- Window: months (ex: 24)

Seed behavior:
- seed_mode: random = different dataset every run (best for portfolio demos)
- seed_mode: fixed + seed: 123 = reproducible (best for tests / CI)

---

## Zero real data policy

* Everything generated here is synthetic.

* Names/emails/IDs look human, but none of it maps to real people or systems.

---
