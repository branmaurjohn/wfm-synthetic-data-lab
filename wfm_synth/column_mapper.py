from __future__ import annotations
import re
from dataclasses import dataclass

def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

# Canonical fields we generate in code
CANON = {
    "personid": ["personid", "person_id", "employeeid", "employee_id", "empid", "employeeidentifier"],
    "employeename": ["employeename", "employee_name", "fullname", "full_name", "name"],
    "email": ["email", "emailaddress", "email_address"],
    "org_path": ["org_path", "orgpath", "organizationpath", "orgstructurepath", "businessstructurepath"],
    "facility_code": ["facility_code", "facilitycode", "facility", "facilityid", "sitecode", "site_code"],
    "unit_code": ["unit_code", "unitcode", "unit", "unitid", "deptcode", "dept_code", "departmentcode"],
    "costcenter": ["costcenter", "cost_center", "costcentre", "cost_centre"],
    "positioncode": ["positioncode", "position_code", "jobcode", "job_code", "position"],
    "workdate": ["workdate", "work_date", "date", "applydate", "asofdate", "as_of_date"],
    "scheduledhours": ["scheduledhours", "scheduled_hours", "schedhours", "schedulehours"],
    "workedhours": ["workedhours", "worked_hours", "actualhours", "actual_hours", "hoursworked", "workhours"],
    "paidhours": ["paidhours", "paid_hours"],
    "variancehours": ["variancehours", "variance_hours", "variance"],
    "accrualcode": ["accrualcode", "accrual_code", "accrual"],
    "balancehours": ["balancehours", "balance_hours", "balance"],
    "nodepath": ["nodepath", "node_path", "path"],
    "nodename": ["nodename", "node_name", "name"],
    "level": ["level", "nodelevel", "node_level"],
}

@dataclass
class Mapping:
    # canonical -> real target column
    canon_to_profile: dict[str, str]

def build_mapping(profile_cols: list[str]) -> Mapping:
    prof_norm = {norm(c): c for c in profile_cols}
    canon_to_profile: dict[str, str] = {}

    # Try to match each canonical key to a profile column based on synonyms
    for canon_key, syns in CANON.items():
        hit = None
        for s in syns:
            ns = norm(s)
            if ns in prof_norm:
                hit = prof_norm[ns]
                break
        # fallback: direct normalized match
        if hit is None and canon_key in prof_norm:
            hit = prof_norm[canon_key]
        if hit is not None:
            canon_to_profile[canon_key] = hit

    return Mapping(canon_to_profile=canon_to_profile)

def apply_mapping_row(row: dict, mapping: Mapping) -> dict:
    """
    Takes a row with canonical keys (personId, costCenter, workDate, etc)
    and returns a row using profile column names where we know them.
    Unmapped fields keep their original keys.
    """
    out = {}
    for k, v in row.items():
        nk = norm(k)
        target = mapping.canon_to_profile.get(nk)
        out[target if target else k] = v
    return out
