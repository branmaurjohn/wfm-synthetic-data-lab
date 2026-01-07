from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import math
import random
from datetime import date, timedelta
import pandas as pd

from wfm_synth.config import GeneratorConfig
from wfm_synth.seed import derive_seed, rng
from wfm_synth.people import generate_people
from wfm_synth.ids import cost_center_8, position_code

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

def _daterange(end_inclusive: date, days: int):
    for i in range(days):
        yield end_inclusive - timedelta(days=(days - 1 - i))

def _safe_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def build_org_path(company: str, state: str, market: str, facility_name: str, facility_code: str, service_line: str, unit_name: str, unit_code: str, job: str):
    # AHS/OK/OK/SOUTH 5265/CC/Intensive Care Unit - 1004/RN
    # You described as Company/Region/Market/Facility/Service Line/Unit/Job
    return f"{company}/{state}/{market}/{facility_name} {facility_code}/{service_line}/{unit_name} - {unit_code}/{job}"

def load_schema_snapshot(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))

def generate_vtimecardtotal(cfg: GeneratorConfig, schema: dict, out_dir: Path) -> Path:
    seed_ctx = derive_seed(cfg.seed_mode, cfg.seed)
    r = rng(seed_ctx.seed)

    # people
    people = generate_people(cfg.population.employees, r, company_domain="ahs-demo.org")

    # time window
    end_date = date.today()
    days = int(cfg.window.months * 30.4375)  # avg days per month
    days = max(1, days)

    rows = []
    for p in people:
        unit = _pick_unit(cfg.units, r)

        cc = cost_center_8(cfg.facility.facility_code, unit.unit_code)     # 8 digits
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

        # baseline schedule/work patterns
        base_daily_hours = r.choice([8.0, 8.0, 8.0, 10.0, 12.0])
        work_prob = 5/7  # avg 5 days per week

        for d in _daterange(end_date, days):
            if r.random() > work_prob:
                continue

            # create realistic variation
            scheduled = base_daily_hours + r.uniform(-0.5, 0.5)
            worked = max(0.0, scheduled + r.uniform(-1.5, 2.0))

            # occasionally add OT
            if r.random() < 0.08:
                worked += r.uniform(0.5, 4.0)

            # paid hours roughly worked minus unpaid break (for non-12s we still can model)
            unpaid_break = 0.5 if worked >= 6 else 0.0
            paid = max(0.0, worked - unpaid_break)

            rows.append({
                "personId": p.personId,
                "employeeName": p.full_name,
                "email": p.email,
                "org_path": org_path,
                "facility_code": cfg.facility.facility_code,
                "unit_code": unit.unit_code,
                "costCenter": cc,
                "PositionCode": pc,
                "workDate": d.isoformat(),
                "scheduledHours": round(scheduled, 2),
                "workedHours": round(worked, 2),
                "paidHours": round(paid, 2),
                "varianceHours": round(worked - scheduled, 2),
            })

    df = pd.DataFrame(rows)

    # Conform to schema snapshot columns (create missing cols as null)
    schema_cols = [c["name"] for c in schema.get("columns", [])]
    if not schema_cols:
        raise ValueError("Schema snapshot has no columns")

    # map our known fields to likely schema names where possible
    # If your schema uses different casing, we'll just create nulls for unknowns.
    # We'll keep our generated fields AND align to snapshot output by adding missing.
    for col in schema_cols:
        if col not in df.columns:
            df[col] = None

    # reorder to schema snapshot first, then extras
    ordered = schema_cols + [c for c in df.columns if c not in schema_cols]
    df = df[ordered]

    out_dir.mkdir(parents=True, exist_ok=True)

    # write run metadata + data
    meta = {
        "run_name": cfg.run_name,
        "seed_mode": cfg.seed_mode,
        "seed": seed_ctx.seed,
        "employees": cfg.population.employees,
        "months": cfg.window.months,
        "table": schema.get("table"),
        "unique_identifier": schema.get("unique_identifier"),
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    out_path = out_dir / "vTimecardTotal.csv"
    df.to_csv(out_path, index=False)
    return out_path
