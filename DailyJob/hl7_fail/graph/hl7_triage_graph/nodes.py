"""Graph nodes. Each takes the state and returns a partial update."""
from __future__ import annotations

import json
import sys
from datetime import date as _date
from pathlib import Path
from typing import Any

from . import db, pricing, report
from .config import Settings, load_settings
from .llm import ClaudeError, ask_json
from .resolve import resolve_record
from .state import TriageState

_settings: Settings | None = None


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def configure(s: Settings) -> None:
    global _settings
    _settings = s


# --- preflight -----------------------------------------------------------------

def preflight(state: TriageState) -> dict[str, Any]:
    s = settings()
    today = state.get("date") or _date.today().isoformat()
    update: dict[str, Any] = {"date": today, "lookback_hours": state.get("lookback_hours") or 72}
    if not s.db_configured:
        update.update(db_status="unconfigured",
                      blocked_reason=f"LIS_EMR_DB_PASSWORD missing in {s.env_file}")
        return update
    if not db.db_reachable(s):
        update.update(db_status="down",
                      blocked_reason=f"{s.db_host}:{s.db_port} unreachable (VPN down?)")
        return update
    update.update(db_status="up", log=[f"preflight ok: {s.db_host}:{s.db_port}"])
    return update


def route_after_preflight(state: TriageState) -> str:
    return "fetch_failed" if state.get("db_status") == "up" else "write_blocked_report"


# --- data ----------------------------------------------------------------------

def fetch_failed(state: TriageState) -> dict[str, Any]:
    s = settings()
    conn = db.connect(s)
    try:
        rows = db.fetch_failed_rows(conn, int(state.get("lookback_hours") or 72))
        quarantine = db.fetch_quarantine(conn, [int(r["id"]) for r in rows])
    finally:
        conn.close()
    for r in rows:
        r["id"] = int(r["id"])
        r["quarantine"] = quarantine.get(r["id"])
    return {"records": rows, "log": [f"fetch_failed: {len(rows)} rows, {len(quarantine)} quarantine rows"]}


def route_after_fetch(state: TriageState) -> str:
    return "classify" if state.get("records") else "write_report"


def classify(state: TriageState) -> dict[str, Any]:
    buckets: dict[str, list[int]] = {"A": [], "CNF": [], "B": [], "C": []}
    for r in state.get("records") or []:
        if r.get("emr_code_not_found"):
            buckets["A"].append(r["id"])
        elif r.get("customer_not_found"):
            buckets["CNF"].append(r["id"])
        elif r.get("order_input"):
            buckets["B"].append(r["id"])
        else:
            buckets["C"].append(r["id"])
    return {"classified": buckets,
            "log": ["classify: " + ", ".join(f"{k}={len(v)}" for k, v in buckets.items())]}


def resolve_customer(state: TriageState) -> dict[str, Any]:
    s = settings()
    conn = db.connect(s)
    resolutions: dict[int, dict[str, Any]] = {}
    try:
        for r in state.get("records") or []:
            resolutions[r["id"]] = resolve_record(conn, r, r.get("quarantine"))
    finally:
        conn.close()
    resolved = sum(1 for v in resolutions.values() if v.get("winner"))
    return {"resolutions": resolutions,
            "log": [f"resolve_customer: {resolved}/{len(resolutions)} resolved to a winner"]}


def lookup_codes(state: TriageState) -> dict[str, Any]:
    s = settings()
    ids = (state.get("classified") or {}).get("A", [])
    if not ids:
        return {"code_lookups": {}, "pricing_status": "skipped (no Type A)"}
    if not s.pricing_token:
        return {"code_lookups": {}, "pricing_status": "token missing (PRICING_API_TOKEN / orderApi.yaml)"}
    try:
        catalog = pricing.load_catalog(s.pricing_token)
    except Exception as exc:  # noqa: BLE001 - any failure here must land in the report, not kill the run
        return {"code_lookups": {}, "pricing_status": f"load failed: {exc!r}"}
    records = {r["id"]: r for r in state.get("records") or []}
    resolutions = state.get("resolutions") or {}
    lookups: dict[int, list[dict[str, Any]]] = {}
    for i in ids:
        winner = (resolutions.get(i) or {}).get("winner") or {}
        flagged = pricing.split_codes(records[i].get("emr_code_not_found"))
        # The whole order is blocked by the flagged code(s), but the retry only
        # succeeds if every OBR code on the order resolves, so the sibling
        # codes from the quarantined raw HL7 are checked too.
        obr = (records[i].get("quarantine") or {}).get("obr_codes") or []
        codes = list(dict.fromkeys(flagged + [c for c in obr if c not in flagged]))
        lookups[i] = []
        for c in codes:
            entry = pricing.lookup_code(catalog, c, winner.get("customer_id"), winner.get("clinic_id"))
            entry["flagged"] = c in flagged
            lookups[i].append(entry)
    return {"code_lookups": lookups, "pricing_status": catalog.summary,
            "log": [f"lookup_codes: {sum(len(v) for v in lookups.values())} codes across {len(lookups)} records"]}


# --- report --------------------------------------------------------------------

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "overall": {"type": "string"},
        "sections": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in ("A", "CNF", "B", "C")},
            "required": ["A", "CNF", "B", "C"],
            "additionalProperties": False,
        },
        "prescriptions": {"type": "array", "items": {"type": "string"}},
        "confidence_notes": {"type": "string"},
    },
    "required": ["overall", "sections", "prescriptions", "confidence_notes"],
    "additionalProperties": False,
}

NARRATIVE_INSTRUCTIONS = """You are writing the analysis part of a daily triage report for failed inbound HL7 orders at a clinical lab (Vibrant America, LIS). The facts below were established by deterministic code against the production database and the pricing catalog. Your job is to explain them, not to re-derive or extend them.

Rules:
- Write in Traditional Chinese (zh-TW). Keep identifiers, table/column names, codes and ids exactly as given.
- Never invent ids, customers, codes, dates or counts. Only reference what is in the facts. If something is unknown, say it is unknown.
- Type A diagnoses are already decided per code: `code_missing` (needs pricing to register the code or an alias), `not_orderable` (code exists but isOrderable=false / priceVa gap: a catalog configuration gap, NOT a missing code), `not_assigned` (custom bundle bound to a different customer/clinic than the one the order resolves to), `ok` (this code is fine; something else blocked the order). Keep those distinctions; they send different teams to work.
- In `code_lookups`, `flagged: true` marks the code(s) emr-v2 recorded in emr_code_not_found; `flagged: false` entries are the other OBR codes on the same order, checked so a retry does not fail on them. Report sibling codes briefly (ok / not ok); do not present them as the cause unless their diagnosis is not `ok`.
- For records where `competing` is true, explain that the NPI has several LIVE ordering integrations and which one wins and why (FULL_INTEGRATION before ORDER_ONLY, then newest updated_at), and that a bundle bound to the losing customer is a known cause of emr_code_not_found.
- For `ambiguous` resolutions, say ownership could not be determined and list what was tried.
- customer_not_found records: the provider has no ehr_integrations row; the fix is the add-provider integration playbook, then re-placing via retry_num. Do not describe it as done.
- Type B: the graph did not execute any payment/order recovery. Say that recovery is pending manual action.
- Prescriptions are proposals for Leo to decide. Nothing was changed. Do not phrase them as completed actions.
- Group identical root causes across records instead of repeating the same paragraph per record.
- `sections.X` is markdown for that class; use an empty string when the class has no records. Short paragraphs and bullet lists; no headings inside sections.
- `overall`: 2 to 5 sentences summarizing what happened today and the single most important action.
- `confidence_notes`: what the evidence does not cover (for example a code that disappeared from the catalog between runs cannot be dated from today's data alone).
"""


def _facts(state: TriageState) -> dict[str, Any]:
    records = []
    resolutions = state.get("resolutions") or {}
    lookups = state.get("code_lookups") or {}
    classes = {i: cls for cls, ids in (state.get("classified") or {}).items() for i in ids}
    for r in state.get("records") or []:
        res = resolutions.get(r["id"]) or {}
        slim_res = {k: res.get(k) for k in ("npi", "npi_source", "lookup_key", "winner", "competing", "ambiguous", "note")}
        slim_res["candidates"] = [
            {k: c.get(k) for k in ("id", "customer_id", "clinic_id", "customer_npi", "clinic_name",
                                   "integration_type", "legacy_emr_service", "updated_at")}
            for c in (res.get("candidates") or [])[:8]
        ]
        q = r.get("quarantine") or {}
        records.append({
            "id": r["id"], "class": classes.get(r["id"]), "file_name": r.get("file_name"),
            "received_time": r.get("received_time"), "emr_service": r.get("emr_service"),
            "sftpDir": r.get("sftpDir"), "emr_code_not_found": r.get("emr_code_not_found"),
            "customer_not_found": r.get("customer_not_found"), "last_error": r.get("last_error"),
            "error_detail": r.get("error_detail"), "has_order_input": bool(r.get("order_input")),
            "quarantine": {k: q.get(k) for k in ("id", "provider_npi", "provider_name", "patient_name", "order_id",
                                                  "matched_integration_id", "quarantine_reason", "failure_class",
                                                  "status", "expires_at", "obr_codes")} if q else None,
            "resolution": slim_res,
            "code_lookups": lookups.get(r["id"], []),
        })
    return {
        "date": state.get("date"),
        "lookback_hours": state.get("lookback_hours"),
        "counts": report.summary_counts(state),
        "pricing_status": state.get("pricing_status"),
        "records": records,
    }


def write_report(state: TriageState) -> dict[str, Any]:
    s = settings()
    update: dict[str, Any] = {}
    if state.get("records") and state.get("use_llm", True):
        prompt = NARRATIVE_INSTRUCTIONS + "\n\nFACTS (JSON):\n" + json.dumps(_facts(state), ensure_ascii=False, indent=1)
        try:
            update["narrative"] = ask_json(prompt, NARRATIVE_SCHEMA, s.model)
            update["log"] = ["write_report: narrative from claude -p"]
        except ClaudeError as exc:
            update["llm_error"] = str(exc)
            update["log"] = [f"write_report: LLM failed, deterministic report only: {exc}"]
    elif state.get("records"):
        update["log"] = ["write_report: LLM disabled, deterministic report only"]
    merged = {**state, **update}
    md = report.render_report(merged)
    path = _write(s.out_dir, merged["date"], md)
    update.update(report_md=md, report_path=str(path))
    return update


def write_blocked_report(state: TriageState) -> dict[str, Any]:
    s = settings()
    md = report.render_blocked_report(state["date"], state.get("blocked_reason") or "unknown")
    path = _write(s.out_dir, state["date"], md)
    return {"report_md": md, "report_path": str(path), "log": [f"blocked: {state.get('blocked_reason')}"]}


def _write(out_dir: Path, date: str, md: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"triage_{date}.md"
    path.write_text(md)
    return path


# --- mail ----------------------------------------------------------------------

def send_mail(state: TriageState) -> dict[str, Any]:
    if state.get("dry_run"):
        return {"mail_status": "skipped (dry run)", "log": ["send_mail: skipped (dry run)"]}
    mailer_dir = Path(__file__).resolve().parents[2]  # DailyJob/hl7_fail
    if str(mailer_dir) not in sys.path:
        sys.path.insert(0, str(mailer_dir))
    try:
        from send_triage_mail import send_report_file  # type: ignore
    except ImportError as exc:
        return {"mail_status": f"mailer unavailable: {exc}", "log": [f"send_mail: {exc}"]}
    rc, detail = send_report_file(Path(state["report_path"]), state["date"])
    status = {0: "sent", 1: "sent (no-report alert)", 2: "not configured", 3: "smtp failure"}.get(rc, f"rc={rc}")
    return {"mail_status": f"{status}: {detail}", "log": [f"send_mail: {status}: {detail}"]}
