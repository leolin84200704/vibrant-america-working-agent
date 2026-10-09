"""CLI entry point.

  python -m hl7_triage_graph                 # today, full run, mails the report
  python -m hl7_triage_graph --dry-run       # no mail
  python -m hl7_triage_graph --no-llm        # deterministic report only
  python -m hl7_triage_graph --print-graph   # mermaid of the wiring
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import nodes
from .config import DEFAULT_LOOKBACK_HOURS, load_settings
from .graph import build_graph


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="hl7_triage_graph")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--lookback-hours", type=int, default=DEFAULT_LOOKBACK_HOURS)
    ap.add_argument("--out-dir", type=Path, default=None, help="default: DailyJob/hl7_fail under the agent root")
    ap.add_argument("--dry-run", action="store_true", help="write the report but do not mail it")
    ap.add_argument("--no-llm", action="store_true", help="skip the claude -p narrative node")
    ap.add_argument("--print-graph", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    nodes.configure(load_settings(out_dir=args.out_dir))
    graph = build_graph()
    if args.print_graph:
        print(graph.get_graph().draw_mermaid())
        return 0

    final = graph.invoke({
        "date": args.date,
        "lookback_hours": args.lookback_hours,
        "dry_run": args.dry_run,
        "use_llm": not args.no_llm,
        "log": [],
    })
    if not args.quiet:
        for line in final.get("log", []):
            print(f"[graph] {line}")
        print(f"[graph] report: {final.get('report_path')}")
        print(f"[graph] mail: {final.get('mail_status')}")
    if final.get("db_status") != "up":
        return 1
    if final.get("llm_error"):
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
