from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

import pandas as pd

from wfm_synth.spc_config import ScenarioConfig


def _check_bounds(value: float, target: float, tolerance: float) -> bool:
    lower = max(0.0, target - tolerance)
    upper = min(1.0, target + tolerance)
    return lower <= value <= upper


def run_health_checks(tables: Dict[str, pd.DataFrame], cfg: ScenarioConfig) -> Dict[str, object]:
    employees = tables["employee"]
    org_units = tables["org_unit"]
    schedule = tables["schedule"]
    timecard = tables["timecard"]

    start_date = pd.to_datetime(cfg.time_window.start).date()
    end_date = pd.to_datetime(cfg.time_window.end).date()

    checks: List[Dict[str, object]] = []

    def add_check(check_id: str, severity: str, passed: bool, details: Dict[str, object]) -> None:
        checks.append(
            {
                "check_id": check_id,
                "severity": severity,
                "status": "PASS" if passed else "FAIL",
                "details": details,
            }
        )

    emp_ids = set(employees["person_id"])
    org_ids = set(org_units["org_id"])

    timecard_orphan_emp = timecard.loc[~timecard["person_id"].isin(emp_ids), "person_id"].nunique()
    add_check(
        "fk_timecard_employee",
        "ERROR",
        timecard_orphan_emp == 0,
        {"orphan_employees": int(timecard_orphan_emp)},
    )

    timecard_orphan_org = timecard.loc[~timecard["org_id"].isin(org_ids), "org_id"].nunique()
    add_check(
        "fk_timecard_org",
        "ERROR",
        timecard_orphan_org == 0,
        {"orphan_orgs": int(timecard_orphan_org)},
    )

    schedule_orphan_emp = schedule.loc[~schedule["person_id"].isin(emp_ids), "person_id"].nunique()
    add_check(
        "fk_schedule_employee",
        "ERROR",
        schedule_orphan_emp == 0,
        {"orphan_employees": int(schedule_orphan_emp)},
    )

    schedule_orphan_org = schedule.loc[~schedule["org_id"].isin(org_ids), "org_id"].nunique()
    add_check(
        "fk_schedule_org",
        "ERROR",
        schedule_orphan_org == 0,
        {"orphan_orgs": int(schedule_orphan_org)},
    )

    timecard_dates = pd.to_datetime(timecard["work_date"]).dt.date
    out_of_window = ((timecard_dates < start_date) | (timecard_dates > end_date)).sum()
    add_check(
        "timecard_date_in_window",
        "ERROR",
        out_of_window == 0,
        {"out_of_window": int(out_of_window)},
    )

    reg_hours = timecard.loc[timecard["pay_code"].isin(["REG", "OT"]), "hours"].sum()
    ot_hours = timecard.loc[timecard["pay_code"] == "OT", "hours"].sum()
    total_sched = schedule["scheduled_hours"].sum()
    absence_hours = timecard.loc[timecard["pay_code"] == "ABS", "hours"].sum()
    callout_hours = timecard.loc[timecard["pay_code"] == "CALL", "hours"].sum()

    ot_rate = float(ot_hours / reg_hours) if reg_hours else 0.0
    absence_rate = float(absence_hours / total_sched) if total_sched else 0.0
    callout_rate = float(callout_hours / total_sched) if total_sched else 0.0

    schedule_dates = pd.to_datetime(schedule["work_date"]).dt.date
    weekend_sched = schedule_dates.apply(lambda d: d.weekday() >= 5).sum()
    weekend_rate = float(weekend_sched / len(schedule)) if len(schedule) else 0.0

    add_check(
        "ratio_ot_rate",
        "WARN",
        _check_bounds(ot_rate, cfg.rates.ot_rate, 0.05),
        {"observed": ot_rate, "target": cfg.rates.ot_rate},
    )
    add_check(
        "ratio_absence_rate",
        "WARN",
        _check_bounds(absence_rate, cfg.rates.absence_rate, 0.05),
        {"observed": absence_rate, "target": cfg.rates.absence_rate},
    )
    add_check(
        "ratio_callout_rate",
        "WARN",
        _check_bounds(callout_rate, cfg.rates.callout_rate, 0.03),
        {"observed": callout_rate, "target": cfg.rates.callout_rate},
    )
    add_check(
        "ratio_weekend_rate",
        "WARN",
        _check_bounds(weekend_rate, cfg.rates.weekend_shift_rate, 0.1),
        {"observed": weekend_rate, "target": cfg.rates.weekend_shift_rate},
    )

    summary = {"INFO": 0, "WARN": 0, "ERROR": 0}
    for check in checks:
        if check["status"] == "FAIL":
            summary[check["severity"]] += 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": cfg.scenario,
        "summary": summary,
        "checks": checks,
    }

    return report


def render_health_report_md(report: Dict[str, object]) -> str:
    lines = [f"# Health Report: {report['scenario']}", "", "## Summary"]
    summary = report["summary"]
    lines.append(f"- ERROR: {summary['ERROR']}")
    lines.append(f"- WARN: {summary['WARN']}")
    lines.append(f"- INFO: {summary['INFO']}")
    lines.append("\n## Checks")

    for check in report["checks"]:
        lines.append(f"- **{check['check_id']}** ({check['severity']}) - {check['status']}")
        details = check.get("details", {})
        if details:
            lines.append(f"  - Details: {details}")

    return "\n".join(lines) + "\n"
