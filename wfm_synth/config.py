from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import yaml

@dataclass
class FacilityConfig:
    company: str
    state: str
    market: str
    facility_name: str
    facility_code: str  # 4 digits as string (e.g., "5265")
    service_line: str

@dataclass
class UnitConfig:
    unit_name: str
    unit_code: str      # 4 digits as string (e.g., "1004")
    job: str            # RN, EVS, HR_RECRUITER, etc.
    headcount_weight: float = 1.0

@dataclass
class PopulationConfig:
    employees: int
    promotions_rate: float = 0.05   # 0-0.90
    attrition_rate: float = 0.08    # 0-0.90
    termination_rate: float = 0.02  # 0-0.90

@dataclass
class TimeWindowConfig:
    months: int

@dataclass
class GeneratorConfig:
    run_name: str
    seed_mode: str = "random"  # random | fixed
    seed: Optional[int] = None
    facility: FacilityConfig = None
    units: List[UnitConfig] = field(default_factory=list)
    population: PopulationConfig = None
    window: TimeWindowConfig = None

def load_config(path: str) -> GeneratorConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    facility = FacilityConfig(**raw["facility"])
    units = [UnitConfig(**u) for u in raw["units"]]
    population = PopulationConfig(**raw["population"])
    window = TimeWindowConfig(**raw["window"])

    return GeneratorConfig(
        run_name=raw.get("run_name", "run"),
        seed_mode=raw.get("seed_mode", "random"),
        seed=raw.get("seed"),
        facility=facility,
        units=units,
        population=population,
        window=window
    )
