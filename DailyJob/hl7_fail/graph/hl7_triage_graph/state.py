"""Graph state. Every node reads the whole state and returns a partial update."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class TriageState(TypedDict, total=False):
    # inputs
    date: str
    lookback_hours: int
    dry_run: bool            # skip the mail node
    use_llm: bool            # False -> deterministic report only
    # preflight
    db_status: str           # "up" | "down" | "unconfigured"
    blocked_reason: str
    # data
    records: list[dict[str, Any]]        # hl7_file_input rows + quarantine info
    classified: dict[str, list[int]]     # class -> record ids
    resolutions: dict[int, dict[str, Any]]   # record id -> customer resolution
    code_lookups: dict[int, list[dict[str, Any]]]  # record id -> per-code lookup
    pricing_status: str
    # output
    narrative: dict[str, Any]
    llm_error: str
    report_md: str
    report_path: str
    mail_status: str
    log: Annotated[list[str], operator.add]
