#!/usr/bin/env python3
"""Email the day's HL7 triage report to Leo.

Transport and credentials are shared with the Ticket Watch mailer
(DailyJob/ticket_watch/send_report.py: REPORT_SMTP_* / REPORT_EMAIL_* in the
agent root's .env). Until those are set this exits 2 and posts a macOS
notification, exactly like the ticket watch mailer.

Used two ways:
- run_triage.sh calls it after the prompt-driven triage (success or BLOCKED)
- the LangGraph runner's send_mail node imports send_report_file()

Exit codes: 0 sent, 1 report missing (alert sent), 2 email not configured,
3 SMTP failure.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

HL7_DIR = Path(__file__).resolve().parent
AGENT_ROOT = HL7_DIR.parents[1]
MAIN_CHECKOUT = Path("/Users/hung.l/src/vibrant-america-working-agent")
TICKET_WATCH_MAILER = HL7_DIR.parent / "ticket_watch" / "send_report.py"


def _load_ticket_watch_mailer():
    spec = importlib.util.spec_from_file_location("ticket_watch_send_report", TICKET_WATCH_MAILER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _env_file() -> Path:
    for candidate in (AGENT_ROOT / ".env", MAIN_CHECKOUT / ".env"):
        if candidate.exists():
            return candidate
    return AGENT_ROOT / ".env"


def subject_for(report_md: str, day: str) -> str:
    head = "\n".join(report_md.splitlines()[:8])
    if "BLOCKED" in head:
        return f"[LIS Agent] HL7 Triage {day} - BLOCKED"
    m = re.search(r"^## Summary\s*\n- (.*)$", report_md, re.MULTILINE)
    tally = m.group(1).strip() if m else ""
    if "No failed records found" in report_md:
        return f"[LIS Agent] HL7 Triage {day} - no failed records"
    return f"[LIS Agent] HL7 Triage {day} - {tally}" if tally else f"[LIS Agent] HL7 Triage {day}"


def send_report_file(report: Path, day: str, dry_run: bool = False) -> tuple[int, str]:
    """Send one report file. Returns (exit_code, detail)."""
    mailer = _load_ticket_watch_mailer()
    env = mailer.load_env(_env_file())

    if report.exists():
        body = report.read_text()
        subject = subject_for(body, day)
        exit_code = 0
    else:
        body = (
            f"# HL7 Triage - {day} - NO REPORT PRODUCED\n\n"
            f"No {report.name} was written. Likely causes: the Mac was asleep, the launchd job is not "
            f"loaded, claude -p failed every attempt, or the VPN pre-flight aborted before writing a report.\n"
            f"Log: {report.parent / f'run_{day}.log'}\n"
        )
        subject = f"[LIS Agent] HL7 Triage {day} - NO REPORT PRODUCED"
        exit_code = 1

    if dry_run:
        return exit_code, f"dry run, would send: {subject}"
    if not env.get("REPORT_SMTP_USER") or not env.get("REPORT_SMTP_PASSWORD"):
        mailer.notify("email not configured - see ticket_watch/README.md")
        return 2, "email not configured: set REPORT_SMTP_USER / REPORT_SMTP_PASSWORD in .env"
    try:
        mailer.send(env, subject, body)
    except Exception as exc:  # noqa: BLE001 - anything here means the mail did not go out
        mailer.notify("SMTP failure - HL7 triage report not sent")
        return 3, f"SMTP failure: {exc!r}"
    return exit_code, f"sent: {subject} -> {env.get('REPORT_EMAIL_TO', mailer.DEFAULT_TO)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--report", type=Path, default=None, help="default: DailyJob/hl7_fail/triage_<date>.md")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    report = args.report or HL7_DIR / f"triage_{args.date}.md"
    rc, detail = send_report_file(report, args.date, dry_run=args.dry_run)
    print(detail, file=sys.stderr if rc in (2, 3) else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main())
