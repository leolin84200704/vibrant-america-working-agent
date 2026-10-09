"""Customer resolution, mirroring emr-v2 resolveOrderingIntegration.

Routing fact (emr-order-customer-resolution skill): the order's customer is
decided by the ORC.12 NPI against ehr_integrations. order_clients is not
consulted. Among LIVE + ordering_enabled rows, FULL_INTEGRATION ranks before
ORDER_ONLY before anything else, then the most recently updated row wins.
"""
from __future__ import annotations

import json
from typing import Any

from . import db

TYPE_RANK = {"FULL_INTEGRATION": 0, "ORDER_ONLY": 1}
NPI_KEYS = ("npi", "providerNpi", "provider_npi", "physicianNpi", "physician_npi",
            "orderingProviderNpi", "ordering_provider_npi", "doctorNpi", "doctor_npi")


def npi_from_order_input(order_input: str | None) -> str | None:
    if not order_input:
        return None
    try:
        data = json.loads(order_input)
    except (ValueError, TypeError):
        return None

    def walk(node: Any) -> str | None:
        if isinstance(node, dict):
            for key in NPI_KEYS:
                value = node.get(key)
                if value and str(value).strip():
                    return str(value).strip()
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    return walk(data)


def rank_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    live = [r for r in rows if r.get("status") == "LIVE" and int(r.get("ordering_enabled") or 0) == 1]
    return sorted(
        live,
        key=lambda r: (TYPE_RANK.get(r.get("integration_type"), 2), _neg(r.get("updated_at"))),
    )


def _neg(value: str | None) -> str:
    # Sort helper: later updated_at should come first. ISO strings sort
    # lexicographically, so invert each character.
    text = value or ""
    return "".join(chr(0x10FFFF - ord(ch)) for ch in text)


def resolve_record(conn, record: dict[str, Any], quarantine: dict[str, Any] | None) -> dict[str, Any]:
    """Return the resolution block for one hl7_file_input row."""
    result: dict[str, Any] = {
        "npi": None,
        "npi_source": None,
        "lookup_key": None,
        "candidates": [],
        "all_rows": [],
        "winner": None,
        "ambiguous": False,
        "competing": False,
        "note": "",
    }

    npi = npi_from_order_input(record.get("order_input"))
    source = "order_input" if npi else None
    if not npi and quarantine and quarantine.get("provider_npi"):
        npi = str(quarantine["provider_npi"]).strip()
        source = "quarantined_orders.provider_npi"
    result["npi"] = npi
    result["npi_source"] = source

    rows: list[dict[str, Any]] = []
    if npi:
        if len(npi) == 10 and npi.isdigit():
            rows = db.integrations_by_npi(conn, npi)
            result["lookup_key"] = f"npi={npi}"
        if not rows:
            # FollowThatPatient and some vendors put the VA customer id in ORC.12.
            rows = db.integrations_by_customer_id(conn, npi)
            if rows:
                result["lookup_key"] = f"customer_id={npi}"
                result["note"] = "ORC.12 value matched ehr_integrations.customer_id, not an NPI"

    if not rows:
        rows = db.integrations_by_sftp_dir(conn, record.get("sftpDir"))
        result["lookup_key"] = f"sftp_prefix={db.sftp_practice_prefix(record.get('sftpDir'))}"
        result["ambiguous"] = True
        if npi:
            result["note"] = (result["note"] + "; " if result["note"] else "") + \
                f"no ehr_integrations row for ORC.12 value {npi}; listing practice candidates by sftpDir"
        else:
            result["note"] = "no NPI available (order_input NULL, no quarantine row); listing practice candidates by sftpDir"

    result["all_rows"] = rows
    candidates = rank_candidates(rows)
    result["candidates"] = candidates
    if candidates and not result["ambiguous"]:
        result["winner"] = candidates[0]
        result["competing"] = len(candidates) > 1
    return result
