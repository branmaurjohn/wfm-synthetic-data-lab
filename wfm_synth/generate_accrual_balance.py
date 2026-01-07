from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import json
import random
import pandas as pd

from wfm_synth.config import GeneratorConfig
from wfm_synth.seed import derive_seed, rng
from wfm_synth.people import generate_people
from wfm_synth.ids import cost_center_8, position_code
from wfm_synth.generate_timecard_total import build_org_path
from wfm_synth.schema_utils import conform_to_schema

def _pick_unit(units, r: random.Random):
    weights = [max(0.0001, u.headcount_weight) for u in units]
    total = sum(weights)
    x = r.random() * total
    s = 0.0
    for u, w in zip(units, weights):
        s += w
        if x <= s:
            return u
    return units[-1]

def _month_ends(end_date: date, months: int):
    # simple month-end list ending near today, not calendar-perfect but believable
    d = end_date
    for _ in range(months):
        yield d
        d = d - timedelta(days=30)

def generate_vaccrualbalance(cfg, schema_cols, out_dir, profile_cols=None, mapping=None):
    seed_ctx = derive_seed(cfg.seed_mode, cfg.seed)
    r = rng(seed_ctx.seed)

    people = generate_people(cfg.population.employees, r, company_domain="ahs-demo.org")

    accrual_codes = ["PTO", "EIL", "SICK"]
    end_date = date.today()

    rows = []
    for p in people:
        unit = _pick_unit(cfg.units, r)
        cc = cost_center_8(cfg.facility.facility_code, unit.unit_code)
        pc = position_code(cfg.facility.facility_code, unit.unit_code, unit.job)

        org_path = build_org_path(
            cfg.facility.company,
            cfg.facility.state,
            cfg.facility.market,
            cfg.facility.facility_name,
            cfg.facility.facility_code,
            cfg.facility.service_line,
            unit.unit_name,
            unit.unit_code,
            unit.job
        )

        # base balances per person (bounded)
        base = {
            "PTO": r.uniform(20, 180),
            "EIL": r.uniform(0, 40),
            "SICK": r.uniform(0, 80),
        }

        for as_of in _month_ends(end_date, cfg.window.months):
            for code in accrual_codes:
                # simulate drift and usage
                drift = r.uniform(-8, 12)
                bal = max(0.0, base[code] + drift)

                rows.append({
                    "personId": p.personId,
                    "employeeName": p.full_name,
                    "email": p.email,
                    "org_path": org_path,
                    "facility_code": cfg.facility.facility_code,
                    "unit_code": unit.unit_code,
                    "costCenter": cc,
                    "PositionCode": pc,
                    "accrualCode": code,
                    "asOfDate": as_of.isoformat(),
                    "balanceHours": round(bal, 2),
                })

                # carry forward a bit
                base[code] = bal

    df = pd.DataFrame(rows)
    df = conform_to_schema(df, schema_cols)

    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "run_name": cfg.run_name,
        "seed_mode": cfg.seed_mode,
        "seed": seed_ctx.seed,
        "employees": cfg.population.employees,
        "months": cfg.window.months,
        "table": "vAccrualBalance",
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    out_path = out_dir / "vAccrualBalance.csv"
    df.to_csv(out_path, index=False)
    return out_path
