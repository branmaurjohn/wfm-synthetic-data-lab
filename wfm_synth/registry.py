from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class TableSpec:
    table: str
    depends_on: List[str]
    # generator signature is intentionally generic; orchestrator handles args per table
    generator_key: str


def get_table_specs() -> Dict[str, TableSpec]:
    """
    Registry of supported tables + generation ordering.

    Add new tables here as you implement new generators.
    """
    specs = [
        TableSpec(
            table="vDimBusinessStructure",
            depends_on=[],
            generator_key="dim_business_structure",
        ),
        TableSpec(
            table="vTimecardTotal",
            depends_on=["vDimBusinessStructure"],
            generator_key="timecard_total",
        ),
        TableSpec(
            table="vAccrualBalance",
            depends_on=["vDimBusinessStructure"],
            generator_key="accrual_balance",
        ),
    ]
    return {s.table: s for s in specs}
