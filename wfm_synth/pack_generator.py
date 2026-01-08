from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from faker import Faker

from wfm_synth.health_checks import render_health_report_md, run_health_checks
from wfm_synth.spc_config import ScenarioConfig, load_spc_scenario


PAY_CODES = [
    {"pay_code": "REG", "pay_code_name": "Regular", "pay_category": "REGULAR"},
    {"pay_code": "OT", "pay_code_name": "Overtime", "pay_category": "OVERTIME"},
    {"pay_code": "ABS", "pay_code_name": "Absence", "pay_category": "ABSENCE"},
    {"pay_code": "CALL", "pay_code_name": "Callout", "pay_category": "CALLOUT"},
]

GRAIN_NOTES = {
    "employee": "1 row per employee",
    "org_unit": "1 row per org unit",
    "schedule": "1 row per employee per scheduled day",
    "timecard": "1 row per employee per pay code per day",
    "pay_code": "1 row per pay code",
    "labor_daily": "1 row per employee per org per day",
}

KEY_MAP = {
    "employee": ["person_id"],
    "org_unit": ["org_id"],
    "schedule": ["person_id", "org_id", "work_date"],
    "timecard": ["person_id", "org_id", "work_date"],
    "pay_code": ["pay_code"],
    "labor_daily": ["person_id", "org_id", "work_date"],
}


def _seed_all(seed: str | int | None) -> int:
    if seed is None:
        seed_value = int(datetime.now(timezone.utc).timestamp())
    elif isinstance(seed, int):
        seed_value = seed
    else:
        seed_value = abs(hash(seed)) % (2**32)
    np.random.seed(seed_value)
    Faker.seed(seed_value)
    return seed_value


def _date_range(start: str, end: str) -> List[pd.Timestamp]:
    return list(pd.date_range(start=start, end=end, freq="D"))


def _weighted_choice(items: List[str], weights: List[float]) -> str:
    return str(np.random.choice(items, p=np.array(weights) / sum(weights)))


def _build_org_units(cfg: ScenarioConfig) -> pd.DataFrame:
    rows = []
    for unit in cfg.org_units:
        rows.append(
            {
                "org_id": unit.org_id,
                "org_name": unit.org_name,
                "unit_type": unit.unit_type,
                "parent_org_id": None,
            }
        )
    return pd.DataFrame(rows)


def _build_pay_codes() -> pd.DataFrame:
    return pd.DataFrame(PAY_CODES)


def _build_employees(cfg: ScenarioConfig, faker: Faker) -> pd.DataFrame:
    org_ids = [unit.org_id for unit in cfg.org_units]
    org_weights = np.array([1.0 for _ in cfg.org_units])
    org_weights = org_weights / org_weights.sum()

    start_date = pd.to_datetime(cfg.time_window.start).date()
    end_date = pd.to_datetime(cfg.time_window.end).date()
    hire_start = start_date - timedelta(days=90)
    hire_end = end_date

    rows = []
    for idx in range(cfg.headcount):
        org_id = str(np.random.choice(org_ids, p=org_weights))
        unit = next(unit for unit in cfg.org_units if unit.org_id == org_id)
        job_codes = list(unit.job_mix.keys())
        job_weights = list(unit.job_mix.values())
        job_code = _weighted_choice(job_codes, job_weights)

        hire_date = faker.date_between(hire_start, hire_end)
        status = "ACTIVE" if np.random.random() < 0.95 else "INACTIVE"

        rows.append(
            {
                "person_id": f"P{idx + 1:05d}",
                "employee_id": f"E{idx + 1:05d}",
                "org_id": org_id,
                "job_code": job_code,
                "hire_date": hire_date.isoformat(),
                "status": status,
            }
        )
    return pd.DataFrame(rows)


def _build_schedule(cfg: ScenarioConfig, employees: pd.DataFrame) -> pd.DataFrame:
    dates = _date_range(cfg.time_window.start, cfg.time_window.end)
    rows = []

    for _, emp in employees.iterrows():
        for work_date in dates:
            is_weekend = work_date.weekday() >= 5
            schedule_prob = cfg.rates.weekend_shift_rate if is_weekend else 0.75
            if np.random.random() > schedule_prob:
                continue

            shift_hours = (
                cfg.shift_patterns.weekend_shift_hours
                if is_weekend
                else cfg.shift_patterns.default_shift_hours
            )
            shift_start_hour = 7 if np.random.random() < 0.7 else 19
            shift_start = datetime.combine(work_date.date(), datetime.min.time()) + timedelta(
                hours=shift_start_hour
            )
            shift_end = shift_start + timedelta(hours=shift_hours)

            rows.append(
                {
                    "schedule_id": f"S{emp.person_id}-{work_date.date().isoformat()}",
                    "person_id": emp.person_id,
                    "org_id": emp.org_id,
                    "work_date": work_date.date().isoformat(),
                    "shift_start": shift_start.isoformat(),
                    "shift_end": shift_end.isoformat(),
                    "scheduled_hours": float(shift_hours),
                }
            )
    return pd.DataFrame(rows)


def _build_timecards(cfg: ScenarioConfig, schedule: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, shift in schedule.iterrows():
        if np.random.random() < cfg.rates.absence_rate:
            rows.append(
                {
                    "timecard_id": f"TC-{shift.schedule_id}-ABS",
                    "person_id": shift.person_id,
                    "org_id": shift.org_id,
                    "work_date": shift.work_date,
                    "pay_code": "ABS",
                    "hours": float(shift.scheduled_hours),
                    "punch_in": None,
                    "punch_out": None,
                }
            )
            continue

        rows.append(
            {
                "timecard_id": f"TC-{shift.schedule_id}-REG",
                "person_id": shift.person_id,
                "org_id": shift.org_id,
                "work_date": shift.work_date,
                "pay_code": "REG",
                "hours": float(shift.scheduled_hours),
                "punch_in": shift.shift_start,
                "punch_out": shift.shift_end,
            }
        )

        if np.random.random() < cfg.rates.callout_rate:
            call_hours = 2.0
            rows.append(
                {
                    "timecard_id": f"TC-{shift.schedule_id}-CALL",
                    "person_id": shift.person_id,
                    "org_id": shift.org_id,
                    "work_date": shift.work_date,
                    "pay_code": "CALL",
                    "hours": call_hours,
                    "punch_in": shift.shift_start,
                    "punch_out": shift.shift_start,
                }
            )

        if np.random.random() < cfg.rates.ot_rate:
            ot_hours = float(np.random.choice([2, 4]))
            rows.append(
                {
                    "timecard_id": f"TC-{shift.schedule_id}-OT",
                    "person_id": shift.person_id,
                    "org_id": shift.org_id,
                    "work_date": shift.work_date,
                    "pay_code": "OT",
                    "hours": ot_hours,
                    "punch_in": shift.shift_end,
                    "punch_out": (
                        pd.to_datetime(shift.shift_end) + timedelta(hours=ot_hours)
                    ).isoformat(),
                }
            )

    return pd.DataFrame(rows)


def _build_labor_daily(schedule: pd.DataFrame, timecard: pd.DataFrame) -> pd.DataFrame:
    schedule_summary = (
        schedule.groupby(["person_id", "org_id", "work_date"], as_index=False)
        .agg({"scheduled_hours": "sum"})
        .rename(columns={"scheduled_hours": "scheduled_hours"})
    )

    tc_pivot = (
        timecard.pivot_table(
            index=["person_id", "org_id", "work_date"],
            columns="pay_code",
            values="hours",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    for col in ["REG", "OT", "ABS", "CALL"]:
        if col not in tc_pivot.columns:
            tc_pivot[col] = 0.0

    tc_pivot["hours_worked"] = tc_pivot["REG"] + tc_pivot["OT"]
    tc_pivot = tc_pivot.rename(
        columns={
            "OT": "ot_hours",
            "ABS": "absence_hours",
            "CALL": "callout_hours",
        }
    )

    merged = schedule_summary.merge(tc_pivot, on=["person_id", "org_id", "work_date"], how="outer")
    merged["scheduled_hours"] = merged["scheduled_hours"].fillna(0)
    for col in ["hours_worked", "ot_hours", "absence_hours", "callout_hours"]:
        merged[col] = merged[col].fillna(0)

    return merged[
        [
            "person_id",
            "org_id",
            "work_date",
            "scheduled_hours",
            "hours_worked",
            "ot_hours",
            "absence_hours",
            "callout_hours",
        ]
    ]


def _metadata_for_table(df: pd.DataFrame) -> Dict[str, object]:
    null_rates = df.isna().mean().to_dict()
    return {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "null_rates": {k: float(v) for k, v in null_rates.items()},
    }


def generate_pack(scenario_path: str, out_base: Path) -> Path:
    cfg = load_spc_scenario(scenario_path)
    seed_value = _seed_all(cfg.seed)
    faker = Faker()

    run_id = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    pack_root = out_base / "packs" / cfg.scenario / run_id
    tables_dir = pack_root / "tables"
    metadata_dir = pack_root / "metadata"
    checks_dir = pack_root / "checks"

    tables_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    checks_dir.mkdir(parents=True, exist_ok=True)

    org_unit = _build_org_units(cfg)
    pay_code = _build_pay_codes()
    employee = _build_employees(cfg, faker)
    schedule = _build_schedule(cfg, employee)
    timecard = _build_timecards(cfg, schedule)
    labor_daily = _build_labor_daily(schedule, timecard)

    table_frames = {
        "employee": employee,
        "org_unit": org_unit,
        "schedule": schedule,
        "timecard": timecard,
        "pay_code": pay_code,
        "labor_daily": labor_daily,
    }

    generation_stats: Dict[str, Dict[str, object]] = {}
    row_counts: Dict[str, int] = {}

    for table, df in table_frames.items():
        table_path = tables_dir / f"{table}.csv"
        df.to_csv(table_path, index=False)

        meta = _metadata_for_table(df)
        (metadata_dir / f"{table}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

        generation_stats[table] = {
            "rows": meta["row_count"],
            "null_rates": meta["null_rates"],
        }
        row_counts[table] = meta["row_count"]

    report = run_health_checks(table_frames, cfg)
    (checks_dir / "health_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (checks_dir / "health_report.md").write_text(render_health_report_md(report), encoding="utf-8")

    manifest = {
        "spc_version": cfg.spc_version,
        "schema_version": cfg.schema_version,
        "metrics_version": cfg.metrics_version,
        "scenario": cfg.scenario,
        "run_id": run_id,
        "seed": cfg.seed,
        "time_window": asdict(cfg.time_window),
        "tables": list(table_frames.keys()),
        "grain_notes": GRAIN_NOTES,
        "key_map": KEY_MAP,
        "generation_stats": generation_stats,
        "data_profile": {"row_counts_by_table": row_counts},
        "generator": {
            "seed_value": seed_value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    (pack_root / "pack_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return pack_root
