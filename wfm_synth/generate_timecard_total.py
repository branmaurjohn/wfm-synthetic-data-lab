from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import random
from typing import Any

import pandas as pd

from wfm_synth.business_structure import BusinessStructureIndex
from wfm_synth.column_mapper import Mapping, apply_mapping_row
from wfm_synth.config import GeneratorConfig
from wfm_synth.ids import cost_center_8, position_code
from wfm_synth.people import generate_people
from wfm_synth.seed import derive_seed, rng



def _pick_unit(units, r: random.Random):
    weights = [max(0.0001, float(getattr(u, "headcount_weight", 1.0) or 1.0)) for u in units]
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


def _safe_float(x: Any):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _safe_int(x: Any):
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return int(x)
        return int(float(x))
    except Exception:
        return None


def build_org_path(
    company: str,
    state: str,
    market: str,
    facility_name: str,
    facility_code: str,
    service_line: str,
    unit_name: str,
    unit_code: str,
    job: str,
) -> str:
    return f"{company}/{state}/{market}/{facility_name} {facility_code}/{service_line}/{unit_name} - {unit_code}/{job}"


def load_schema_snapshot(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iso_now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_bool_str(v: Any) -> str:
    return "Y" if bool(v) else "N"



def generate_vtimecardtotal(
    cfg: GeneratorConfig,
    schema: dict,
    out_dir: Path,
    profile_cols=None,
    mapping: Mapping | None = None,
) -> Path:
    """
    Generates a vTimecardTotal-like CSV with:
      - realistic employee identities (synthetic)
      - per-day schedule vs actual behavior
      - hard guarantees for key columns (costCenterId, payCode, partitionDate, etc.)
    """

    seed_ctx = derive_seed(cfg.seed_mode, cfg.seed)
    r = rng(seed_ctx.seed)

    bs = None
    bs_path = _repo_root() / "data" / "reference" / "vDimBusinessStructure.csv"
    if bs_path.exists():
        try:
            bs = BusinessStructureIndex.load(bs_path)
        except Exception:
            bs = None

    people = generate_people(cfg.population.employees, r, company_domain="ahs-demo.org")

    end_date = date.today()
    days = int(max(1, round(cfg.window.months * 30.4375)))  # avg days per month
    start_date = end_date - timedelta(days=days - 1)

    schema_cols = [c["name"] for c in schema.get("columns", [])]
    if not schema_cols:
        raise ValueError("Schema snapshot has no columns")

    anchor = start_date
    while anchor.weekday() != 0:  # 0=Mon
        anchor += timedelta(days=1)

    run_id = f"{cfg.run_name}-{int(datetime.now(timezone.utc).timestamp())}"

    rows: list[dict[str, Any]] = []
    for p in people:
        unit = _pick_unit(cfg.units, r)

        cc8 = cost_center_8(cfg.facility.facility_code, unit.unit_code)
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
            unit.job,
        )

        grounded = None
        if bs is not None:
            try:
                grounded = not bs.find_facility_candidates(str(cfg.facility.facility_code)).empty
            except Exception:
                grounded = None

        base_daily_hours = r.choice([8.0, 8.0, 8.0, 10.0, 12.0])
        work_prob = 5 / 7  # avg 5 days per week

        for d in _daterange(end_date, days):
            if r.random() > work_prob:
                continue

            scheduled = base_daily_hours + r.uniform(-0.5, 0.5)
            worked = max(0.0, scheduled + r.uniform(-1.5, 2.0))

            if r.random() < 0.08:
                worked += r.uniform(0.5, 4.0)

            unpaid_break = 0.5 if worked >= 6 else 0.0
            paid = max(0.0, worked - unpaid_break)

            days_from_anchor = (d - anchor).days
            pp_index = 0 if days_from_anchor < 0 else (days_from_anchor // 14) + 1
            pp_week = 1 if (days_from_anchor % 14) < 7 else 2

            row: dict[str, Any] = {
                "personId": str(p.personId),
                "employeeName": p.full_name,
                "email": p.email,
                "org_path": org_path,
                "facility_code": str(cfg.facility.facility_code),
                "unit_code": str(unit.unit_code),

                "costCenter": str(cc8),
                "costCenterId": str(cc8),       
                "PositionCode": str(pc),           
                "orgId": _safe_int(cc8),           
                "assignmentId": f"A-{p.personId}-{cc8}",
                "laborEntryName1": str(cfg.facility.company),
                "laborEntryName2": str(cfg.facility.state),
                "laborEntryName3": str(cfg.facility.market),
                "laborEntryName4": f"{cfg.facility.facility_name} {cfg.facility.facility_code}",
                "laborEntryName5": str(cfg.facility.service_line),
                "laborEntryName6": f"{unit.unit_name} - {unit.unit_code}",
                "laborEntryDesc1": "Company",
                "laborEntryDesc2": "State",
                "laborEntryDesc3": "Market",
                "laborEntryDesc4": "Facility",
                "laborEntryDesc5": "Service Line",
                "laborEntryDesc6": "Unit",


                "workDate": d.isoformat(),
                "partitionDate": d.isoformat(),    # ✅ not null
                "updateDtm": _iso_now_utc(),

                "scheduledHours": round(scheduled, 2),
                "workedHours": round(worked, 2),
                "paidHours": round(paid, 2),
                "varianceHours": round(worked - scheduled, 2),

                "amountType": "HOURS",
                "payCode": "REG",
                "payCodeId": "REG",
                "combinedPayCodeSwt": _to_bool_str(False),
                "signedOffSwt": _to_bool_str(False),
                "laborTransferSwt": _to_bool_str(False),
                "orgTransferSwt": _to_bool_str(False),
                "isFromCorrection": _to_bool_str(False),
                "wageMultiplier": 1.0,
                "payPeriodNumber": int(pp_index),
                "payPeriodWeek": int(pp_week),
                "hoursAmount": round(worked, 2),
                "daysAmount": None,
                "wages": None,          
                "wageAddition": 0.0,

                "business_structure_grounded": grounded,
                
                "uniqueId": f"{run_id}:{p.personId}:{cc8}:{d.isoformat()}",
            }

            if mapping is not None:
                try:
                    row = apply_mapping_row(row, mapping)
                except TypeError:
                    row = row

            rows.append(row)

    df = pd.DataFrame(rows)

    for col in schema_cols:
        if col not in df.columns:
            df[col] = None

    if "facility_code" in df.columns:
        df["facility_code"] = (
            df["facility_code"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(4)
        )
    if "unit_code" in df.columns:
        df["unit_code"] = (
            df["unit_code"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(4)
        )

    if "costCenterId" in df.columns:
        mask = df["costCenterId"].isna() | df["costCenterId"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "costCenterId"] = (df.loc[mask, "facility_code"] + df.loc[mask, "unit_code"]).astype(str)

    if "costCenter" in df.columns:
        mask = df["costCenter"].isna() | df["costCenter"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "costCenter"] = (df.loc[mask, "facility_code"] + df.loc[mask, "unit_code"]).astype(str)

    if "partitionDate" in df.columns and "workDate" in df.columns:
        mask = df["partitionDate"].isna() | df["partitionDate"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "partitionDate"] = df.loc[mask, "workDate"]

    if "payCode" in df.columns:
        mask = df["payCode"].isna() | df["payCode"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "payCode"] = "REG"

    if "payCodeId" in df.columns:
        mask = df["payCodeId"].isna() | df["payCodeId"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "payCodeId"] = "REG"

    if "amountType" in df.columns:
        mask = df["amountType"].isna() | df["amountType"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "amountType"] = "HOURS"

    if "hoursAmount" in df.columns and "workedHours" in df.columns:
        mask = df["hoursAmount"].isna() | df["hoursAmount"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "hoursAmount"] = df.loc[mask, "workedHours"]

    for flag_col in ["signedOffSwt", "combinedPayCodeSwt", "orgTransferSwt", "laborTransferSwt", "isFromCorrection"]:
        if flag_col in df.columns:
            mask = df[flag_col].isna() | df[flag_col].astype(str).str.strip().isin(["", "nan", "None"])
            df.loc[mask, flag_col] = "N"


    if "updateDtm" in df.columns:
        mask = df["updateDtm"].isna() | df["updateDtm"].astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[mask, "updateDtm"] = _iso_now_utc()

    ordered = schema_cols + [c for c in df.columns if c not in schema_cols]
    df = df[ordered]


    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_name": cfg.run_name,
        "seed_mode": cfg.seed_mode,
        "seed": seed_ctx.seed,
        "employees": cfg.population.employees,
        "months": cfg.window.months,
        "table": schema.get("table"),
        "unique_identifier": schema.get("unique_identifier"),
        "created_at_utc": _iso_now_utc(),
    }
    (out_dir / "run_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    out_path = out_dir / "vTimecardTotal.csv"
    df.to_csv(out_path, index=False)
    return out_path
