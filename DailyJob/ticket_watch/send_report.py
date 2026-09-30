#!/usr/bin/env python3
"""Email the day's Ticket Watch report to Leo.

Runs at 09:00 via launchd (com.lis.ticket-report-mail.plist), independent of the
08:00 analysis job, so a missing report is itself reported instead of silently
producing no email. Transport is plain SMTP with credentials from the agent
root's .env (REPORT_SMTP_* / REPORT_EMAIL_*); see README.md for the Gmail
app-password setup.

Exit codes: 0 sent, 1 report missing (alert sent), 2 email not configured,
3 SMTP failure.
"""
import argparse
import os
import re
import smtplib
import subprocess
import sys
import time
from datetime import date
from email.message import EmailMessage
from html import escape
from pathlib import Path

AGENT_ROOT = Path("/Users/hung.l/src/vibrant-america-working-agent")
REPORT_DIR = AGENT_ROOT / "DailyJob" / "ticket_watch"
DEFAULT_TO = "leolin84200704@gmail.com"


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def notify(text: str) -> None:
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{text}" with title "Ticket Watch mail" sound name "Basso"'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass


def summary_line(markdown: str) -> str:
    # The line right under "## Summary" is the one-line tally the prompt writes.
    m = re.search(r"^## Summary\s*\n(- .*)$", markdown, re.MULTILINE)
    return m.group(1).lstrip("- ").strip() if m else ""


def to_html(markdown: str) -> str:
    # No markdown library on this machine; a readable <pre> beats a dependency.
    return (
        "<html><body style='font-family:-apple-system,Helvetica,Arial,sans-serif'>"
        "<pre style='white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.45'>"
        f"{escape(markdown)}</pre></body></html>"
    )


def send(env: dict, subject: str, body_md: str) -> None:
    host = env.get("REPORT_SMTP_HOST", "smtp.gmail.com")
    port = int(env.get("REPORT_SMTP_PORT", "587"))
    user = env["REPORT_SMTP_USER"]
    password = env["REPORT_SMTP_PASSWORD"]
    sender = env.get("REPORT_EMAIL_FROM", user)
    to = env.get("REPORT_EMAIL_TO", DEFAULT_TO)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body_md)
    msg.add_alternative(to_html(body_md), subtype="html")

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=60) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=60) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--wait-minutes", type=int, default=15,
                    help="poll this long for the report before declaring it missing")
    ap.add_argument("--dry-run", action="store_true", help="print instead of sending")
    args = ap.parse_args()

    env = load_env(AGENT_ROOT / ".env")
    report = REPORT_DIR / f"report_{args.date}.md"

    deadline = time.time() + args.wait_minutes * 60
    while not report.exists() and time.time() < deadline:
        time.sleep(30)

    if report.exists():
        body = report.read_text()
        summary = summary_line(body)
        subject = f"[LIS Agent] Ticket Watch {args.date}"
        if summary:
            subject += f" — {summary}"
        exit_code = 0
    else:
        log = REPORT_DIR / f"run_{args.date}.log"
        body = (
            f"# Ticket Watch - {args.date} - NO REPORT PRODUCED\n\n"
            f"The 08:00 analysis job left no {report.name}.\n"
            f"Likely causes: the Mac was asleep, the launchd job is not loaded, or claude ran past one hour.\n"
            f"Log: {log}\n"
        )
        subject = f"[LIS Agent] Ticket Watch {args.date} - NO REPORT PRODUCED"
        exit_code = 1

    if args.dry_run:
        print(subject)
        print(body)
        return exit_code

    if not env.get("REPORT_SMTP_USER") or not env.get("REPORT_SMTP_PASSWORD"):
        print("email not configured: set REPORT_SMTP_USER / REPORT_SMTP_PASSWORD in .env", file=sys.stderr)
        notify("email not configured — see README")
        return 2

    try:
        send(env, subject, body)
    except Exception as exc:  # noqa: BLE001 — anything here means "mail did not go out"
        print(f"SMTP failure: {exc!r}", file=sys.stderr)
        notify("SMTP failure — report not sent")
        return 3

    print(f"sent: {subject} -> {env.get('REPORT_EMAIL_TO', DEFAULT_TO)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
