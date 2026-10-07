"""Markdown rendering. Facts come from state; the LLM only contributes the
narrative blocks, which are inserted verbatim under the matching section."""
from __future__ import annotations

from typing import Any

CLASS_TITLES = {
    "A": "Type A - EMR Code Not Found",
    "B": "Type B - Payment/Order Failure",
    "C": "Type C - Parse Failure",
    "CNF": "Customer Not Found",
}
DIAGNOSIS_LABEL = {
    "ok": "OK (exists, orderable)",
    "code_missing": "code missing from catalog",
    "not_orderable": "exists but isOrderable=false / priceVa gap",
    "not_assigned": "exists but bound to another customer/clinic",
    "unknown_prefix": "unknown prefix",
}


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        out.append("| " + " | ".join(_cell(v) for v in row) + " |")
    return "\n".join(out)


def summary_counts(state: dict[str, Any]) -> dict[str, int]:
    classified = state.get("classified") or {}
    return {
        "total": len(state.get("records") or []),
        "A": len(classified.get("A", [])),
        "B": len(classified.get("B", [])),
        "C": len(classified.get("C", [])),
        "CNF": len(classified.get("CNF", [])),
    }


def summary_line(counts: dict[str, int]) -> str:
    return (f"Total failed: {counts['total']} | A code-not-found: {counts['A']} | "
            f"B order-failure: {counts['B']} | C parse-failure: {counts['C']} | "
            f"customer-not-found: {counts['CNF']}")


def _resolution_block(res: dict[str, Any] | None) -> str:
    if not res:
        return "- resolution: not attempted"
    lines = [f"- NPI / ORC.12: {_cell(res.get('npi'))} (source: {_cell(res.get('npi_source'))}; lookup {_cell(res.get('lookup_key'))})"]
    winner = res.get("winner")
    if winner:
        lines.append(
            f"- winner: customer_id {winner.get('customer_id')} / clinic_id {winner.get('clinic_id')} / "
            f"npi {winner.get('customer_npi')} / {winner.get('clinic_name')} "
            f"({winner.get('integration_type')}, {winner.get('legacy_emr_service')}, "
            f"integration {winner.get('id')}, updated {winner.get('updated_at')})"
        )
        if res.get("competing"):
            lines.append(f"- WARNING: {len(res.get('candidates', []))} LIVE+ordering candidates share this NPI; "
                         "winner chosen by typeRank then updated_at DESC")
    else:
        lines.append("- winner: UNRESOLVED (ownership ambiguous)")
    if res.get("note"):
        lines.append(f"- note: {res['note']}")
    cands = res.get("candidates") or []
    if (res.get("competing") or res.get("ambiguous")) and cands:
        lines.append("")
        lines.append(_table(
            ["integration", "customer_id", "clinic_id", "npi", "clinic_name", "type", "updated_at"],
            [[c.get("id"), c.get("customer_id"), c.get("clinic_id"), c.get("customer_npi"),
              c.get("clinic_name"), c.get("integration_type"), c.get("updated_at")] for c in cands],
        ))
    return "\n".join(lines)


def _record_table(records: list[dict[str, Any]]) -> str:
    rows = []
    for r in records:
        q = r.get("quarantine") or {}
        rows.append([r.get("id"), r.get("file_name"), r.get("received_time"), r.get("emr_service"),
                     r.get("sftpDir"), q.get("patient_name"), q.get("order_id"),
                     ", ".join(q.get("obr_codes") or []), r.get("last_error")])
    return _table(["id", "file_name", "received_time", "emr_service", "sftpDir", "patient (quarantine)",
                   "order_id", "OBR codes", "last_error"], rows)


def _code_table(lookups: list[dict[str, Any]]) -> str:
    rows = []
    for c in lookups:
        ev = c.get("evidence") or {}
        rows.append(["flagged" if c.get("flagged") else "sibling OBR",
                     c.get("code"), c.get("effective_code") if c.get("effective_code") != c.get("code") else "-",
                     c.get("kind"), "yes" if c.get("found") else "no",
                     ev.get("pkg_id") or ev.get("bundle_id"), ev.get("name"),
                     ev.get("is_orderable"), ev.get("price_va"), ev.get("price_vw"),
                     DIAGNOSIS_LABEL.get(c.get("diagnosis"), c.get("diagnosis")), c.get("detail")])
    return _table(["role", "code", "alias", "kind", "in catalog", "id", "name", "isOrderable", "priceVa", "priceVw",
                   "diagnosis", "detail"], rows)


def render_report(state: dict[str, Any]) -> str:
    date = state.get("date")
    counts = summary_counts(state)
    records = {r["id"]: r for r in state.get("records") or []}
    classified = state.get("classified") or {}
    resolutions = state.get("resolutions") or {}
    lookups = state.get("code_lookups") or {}
    narrative = state.get("narrative") or {}
    sections_text = narrative.get("sections") or {}

    out = [f"# HL7 File Input Daily Triage - {date}", "", "## Summary",
           f"- {summary_line(counts)}",
           f"- lookback: {state.get('lookback_hours')}h, filter parse_finished=0 AND retry_num=0",
           f"- pricing catalog: {state.get('pricing_status') or 'not loaded'}",
           f"- generated by: hl7_triage_graph (LangGraph), LLM narrative: "
           f"{'yes' if narrative else 'no (' + (state.get('llm_error') or 'disabled') + ')'}",
           ""]

    if counts["total"] == 0:
        out.append("No failed records found.")
        out.append("")
        return "\n".join(out)

    if narrative.get("overall"):
        out += [narrative["overall"].strip(), ""]

    for cls in ("A", "CNF", "B", "C"):
        ids = classified.get(cls, [])
        out.append(f"## {CLASS_TITLES[cls]}")
        if not ids:
            out += ["None.", ""]
            continue
        out.append(_record_table([records[i] for i in ids]))
        out.append("")
        for i in ids:
            r = records[i]
            out.append(f"### Record {i} - {r.get('file_name')}")
            out.append(_resolution_block(resolutions.get(i)))
            if cls == "A":
                out.append("")
                out.append(f"emr_code_not_found: `{r.get('emr_code_not_found')}`")
                out.append("")
                out.append(_code_table(lookups.get(i, [])))
            if cls == "CNF":
                out.append(f"- customer_not_found: {r.get('customer_not_found')}")
                out.append("- playbook: add-provider integration (emr-order-customer-resolution skill), then retry_num re-place")
            if cls == "B":
                out.append("- recovery: NOT executed by the graph (prod write); run the recovery path manually")
                out.append(f"- order_input (first 300 chars): `{(r.get('order_input') or '')[:300]}`")
            if cls == "C":
                out.append(f"- error_detail: {r.get('error_detail') or '-'}")
                out.append(f"- pod: {r.get('last_update_pod_name') or '-'}")
            out.append("")
        text = sections_text.get(cls)
        if text:
            out += ["#### Analysis", text.strip(), ""]

    if narrative.get("prescriptions"):
        out.append("## Prescriptions (for Leo to decide; nothing was changed)")
        for item in narrative["prescriptions"]:
            out.append(f"- {item}")
        out.append("")
    if narrative.get("confidence_notes"):
        out += ["## Notes", narrative["confidence_notes"].strip(), ""]
    if state.get("llm_error"):
        out += ["## LLM", f"Narrative unavailable: {state['llm_error']}", ""]
    return "\n".join(out)


def render_blocked_report(date: str, reason: str) -> str:
    return "\n".join([
        f"# HL7 File Input Daily Triage - {date}",
        "",
        "## BLOCKED",
        f"- {reason}",
        "- No DB queries were run. This is NOT a \"no failed records\" result. Re-run after fixing the cause.",
        "- generated by: hl7_triage_graph (LangGraph)",
        "",
    ])
