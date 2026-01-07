from __future__ import annotations

from pathlib import Path
import json
import random
import pandas as pd

from wfm_synth.config import GeneratorConfig
from wfm_synth.seed import derive_seed, rng
from wfm_synth.ids import cost_center_8
from wfm_synth.schema_utils import conform_to_schema

def generate_vdimbusinessstructure(cfg, schema_cols, out_dir, profile_cols=None, mapping=None):
    seed_ctx = derive_seed(cfg.seed_mode, cfg.seed)
    r = rng(seed_ctx.seed)

    rows = []

    # Build a believable hierarchy: Company > State > Market > Facility > ServiceLine > Unit
    company = cfg.facility.company
    state = cfg.facility.state
    market = cfg.facility.market
    facility = f"{cfg.facility.facility_name} {cfg.facility.facility_code}"
    service_line = cfg.facility.service_line

    # Parent nodes
    rows.append({"level": "COMPANY", "nodeName": company, "nodePath": company})
    rows.append({"level": "STATE", "nodeName": state, "nodePath": f"{company}/{state}"})
    rows.append({"level": "MARKET", "nodeName": market, "nodePath": f"{company}/{state}/{market}"})
    rows.append({"level": "FACILITY", "nodeName": facility, "nodePath": f"{company}/{state}/{market}/{facility}"})
    rows.append({"level": "SERVICE_LINE", "nodeName": service_line, "nodePath": f"{company}/{state}/{market}/{facility}/{service_line}"})

    # Unit nodes
    for u in cfg.units:
        cc = cost_center_8(cfg.facility.facility_code, u.unit_code)
        unit_label = f"{u.unit_name} - {u.unit_code}"
        unit_path = f"{company}/{state}/{market}/{facility}/{service_line}/{unit_label}"

        rows.append({
            "level": "UNIT",
            "nodeName": unit_label,
            "nodePath": unit_path,
            "facility_code": cfg.facility.facility_code,
            "unit_code": u.unit_code,
            "costCenter": cc,
        })

    df = pd.DataFrame(rows)
    df = conform_to_schema(df, schema_cols)

    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_name": cfg.run_name,
        "seed_mode": cfg.seed_mode,
        "seed": seed_ctx.seed,
        "table": "vDimBusinessStructure",
        "units": len(cfg.units),
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    out_path = out_dir / "vDimBusinessStructure.csv"
    df.to_csv(out_path, index=False)
    return out_path
