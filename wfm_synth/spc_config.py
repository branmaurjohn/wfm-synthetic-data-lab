from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import yaml


@dataclass
class TimeWindow:
    start: str
    end: str


@dataclass
class RateConfig:
    ot_rate: float
    absence_rate: float
    callout_rate: float
    weekend_shift_rate: float


@dataclass
class ShiftPatternConfig:
    default_shift_hours: int
    weekend_shift_hours: int


@dataclass
class OrgUnitConfig:
    org_id: str
    org_name: str
    unit_type: str
    job_mix: Dict[str, float]


@dataclass
class ScenarioConfig:
    scenario: str
    spc_version: str
    schema_version: str
    metrics_version: str
    seed: str | int | None
    time_window: TimeWindow
    headcount: int
    org_units: List[OrgUnitConfig]
    rates: RateConfig
    shift_patterns: ShiftPatternConfig


def load_spc_scenario(path: str) -> ScenarioConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    time_window = TimeWindow(**raw["time_window"])
    rates = RateConfig(**raw["rates"])
    shift_patterns = ShiftPatternConfig(**raw["shift_patterns"])
    org_units = [OrgUnitConfig(**unit) for unit in raw["org_units"]]

    return ScenarioConfig(
        scenario=raw["scenario"],
        spc_version=raw["spc_version"],
        schema_version=raw["schema_version"],
        metrics_version=raw["metrics_version"],
        seed=raw.get("seed"),
        time_window=time_window,
        headcount=raw["headcount"],
        org_units=org_units,
        rates=rates,
        shift_patterns=shift_patterns,
    )
