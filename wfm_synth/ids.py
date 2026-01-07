from __future__ import annotations
import hashlib

def cost_center_8(facility_code_4: str, unit_code_4: str) -> str:
    # costCenter is 8 digits: FAC(4)+UNIT(4)
    fc = facility_code_4.zfill(4)
    uc = unit_code_4.zfill(4)
    return f"{fc}{uc}"

def position_code(facility_code_4: str, unit_code_4: str, job: str) -> str:
    # Your "PositionCode" = FAC(4)+UNIT(4)+JOBHASH(2) => 10 chars
    # Still deterministic, but not identical to costCenter.
    fc = facility_code_4.zfill(4)
    uc = unit_code_4.zfill(4)
    j = (job or "UNK").upper().encode("utf-8")
    h = int(hashlib.md5(j).hexdigest(), 16) % 100
    return f"{fc}{uc}{h:02d}"

def person_id_int64(i: int) -> int:
    # stable synthetic personId
    return 10_000_000 + i
