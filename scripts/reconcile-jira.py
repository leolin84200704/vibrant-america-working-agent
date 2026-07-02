#!/usr/bin/env python3
"""
Reconcile STM ticket status against Jira ground truth (L3→L4 rule).

STM frontmatter `status:` describes the world at write-time; Jira is the
world. This script fetches each ticket's live Jira status and:
  - always records it as `jira_status` in frontmatter (with --apply)
  - when Jira statusCategory is "Done" but local status is still
    active/blocked/paused → flips local status to `completed`
  - never downgrades a local `completed` (report only)

Credentials from .env in agent root (JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN).

Usage:
  python3 scripts/reconcile-jira.py             # dry-run: report only
  python3 scripts/reconcile-jira.py --apply     # write reconciled status back
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parent.parent
STM_DIR = AGENT_ROOT / "storage" / "short_term_memory"
TICKET_RE = re.compile(r"^[A-Z]+-\d+$")
LOCAL_OPEN_STATUSES = {"active", "blocked", "paused", "pending", "vendor-pending",
                       "paused-awaiting-schema", "paused-awaiting-audit-infra"}

sys.path.insert(0, str(AGENT_ROOT / "scripts"))
scoring = __import__("memory_scoring")


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = AGENT_ROOT / ".env"
    if not env_path.exists():
        sys.exit("ERROR: .env not found in agent root — Jira credentials required. "
                 "This script must run on the machine that has JIRA_* configured.")
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in ("JIRA_SERVER", "JIRA_EMAIL", "JIRA_API_TOKEN") if not env.get(k)]
    if missing:
        sys.exit(f"ERROR: missing in .env: {', '.join(missing)}")
    return env


def fetch_status(server: str, auth_header: str, key: str) -> tuple[str, str] | None:
    """Return (status_name, status_category) or None if not found / no access."""
    url = f"{server.rstrip('/')}/rest/api/2/issue/{key}?fields=status"
    req = urllib.request.Request(url, headers={"Authorization": auth_header,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
        status = data["fields"]["status"]
        return status["name"], status["statusCategory"]["key"]  # key: new/indeterminate/done
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            return None
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes back to STM files")
    args = parser.parse_args()

    env = load_env()
    token = base64.b64encode(f"{env['JIRA_EMAIL']}:{env['JIRA_API_TOKEN']}".encode()).decode()
    auth_header = f"Basic {token}"

    completed, recorded, unreachable, in_sync = [], [], [], 0

    for f in sorted(STM_DIR.glob("*.md")):
        if f.name.startswith("_"):
            continue
        meta = scoring.read_frontmatter(f)
        file_id = str(meta.get("id", f.stem))
        if not TICKET_RE.match(file_id):
            continue  # INCIDENT-*, HL7-TRIAGE-*, etc. have no Jira counterpart

        result = fetch_status(env["JIRA_SERVER"], auth_header, file_id)
        if result is None:
            unreachable.append(file_id)
            continue
        jira_name, jira_category = result
        local = str(meta.get("status", "active"))

        changed = False
        if meta.get("jira_status") != jira_name:
            meta["jira_status"] = jira_name
            changed = True

        if jira_category == "done" and local in LOCAL_OPEN_STATUSES:
            meta["status"] = "completed"
            meta["updated"] = date.today().isoformat()
            completed.append(f"{file_id}: local '{local}' → completed (Jira: {jira_name})")
            changed = True
        elif jira_category != "done" and local == "completed":
            # Never downgrade automatically — a reopened ticket needs a human look.
            recorded.append(f"{file_id}: local completed but Jira says '{jira_name}' — review manually")
        else:
            in_sync += 1

        if changed and args.apply:
            scoring.write_frontmatter(f, meta)

    mode = "APPLIED" if args.apply else "DRY-RUN (use --apply to write)"
    print(f"# Jira reconciliation — {date.today().isoformat()} — {mode}")
    print(f"in sync: {in_sync}")
    print(f"flipped to completed: {len(completed)}")
    for line in completed:
        print(f"  {line}")
    if recorded:
        print(f"needs manual review (Jira reopened?): {len(recorded)}")
        for line in recorded:
            print(f"  {line}")
    if unreachable:
        print(f"not found / no access in Jira: {len(unreachable)}")
        print(f"  {', '.join(unreachable)}")
    if args.apply and completed:
        print("NOTE: run scripts/memory_scoring.py to rebuild indexes after this.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
