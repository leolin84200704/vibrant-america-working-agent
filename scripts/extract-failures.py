#!/usr/bin/env python3
"""
Extract the `## Failures` section from every STM file and consolidate them
into `long-term-memory/failures.md` — a single index keyed by root-cause theme.

Designed to run as part of the dream pipeline (idempotent) and on-demand.
Output file is regenerated each run; do not edit by hand.

Usage:
  python3 scripts/extract-failures.py          # write LTM file
  python3 scripts/extract-failures.py --print  # print to stdout only
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STM_DIR = ROOT / "storage" / "short_term_memory"
LTM_OUT = ROOT / "long-term-memory" / "failures.md"

# Heuristic theme classifier: first match wins.
# Order matters — most specific themes first.
THEMES: list[tuple[str, str, re.Pattern]] = [
    ("build-tooling",       "Build / TypeScript / Tooling",
     re.compile(r"tsc|rootDir|dist[ /]|nest build|webpack|tsconfig|prisma generate|postbuild", re.I)),
    ("prod-side-effects",   "Production side-effects (Kafka / email / SFTP)",
     re.compile(r"prod\b|production|kafka|email send|SFTP|fire-and-forget|HL7 sent|垃圾 HL7", re.I)),
    ("db-migration",        "DB / migration / backfill",
     re.compile(r"migration|backfill|schema\b|psql|prisma migrate|calendar_dev|dirty data|320", re.I)),
    ("scope-communication", "Scope / requirement / PM communication",
     re.compile(r"scope|誤解|否定句|implicit|過去 event|expand|擴大|PM (確認|溝通)|requirement", re.I)),
    ("auth-permission",     "Auth / permission / role",
     re.compile(r"role|permission|admin|clinic user|Forbidden|gate|isClinic|isAdmin", re.I)),
    ("redis-cache",         "Redis / cache / pending list",
     re.compile(r"redis|SREM|SADD|pending|cache|ghost|race", re.I)),
    ("grpc-network",        "gRPC / network / timeout",
     re.compile(r"gRPC|grpc|getaddrinfo|ENOTFOUND|timeout|deadline|UNAVAILABLE", re.I)),
    ("bullmq-queue",        "BullMQ / queue / worker",
     re.compile(r"BullMQ|bullmq|queue|worker|concurrency|Promise\.race", re.I)),
    ("test-mocking",        "Test / mock / spec",
     re.compile(r"jest|mock|spec\.ts|integration test|e2e", re.I)),
    ("graphql-api",         "GraphQL / API design",
     re.compile(r"GraphQL|graphql|resolver|@Args|@Mutation|@Query", re.I)),
]
DEFAULT_THEME = ("other", "Other / uncategorized")

FAILURES_RE = re.compile(
    r"^##\s+Failures\s*$\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL
)
SUB_ENTRY_RE = re.compile(
    r"###\s+(?:\[(?P<date>[\d\- :]+)\]\s+)?(?P<title>.+?)\s*$", re.MULTILINE
)


def extract_section(text: str) -> str | None:
    m = FAILURES_RE.search(text)
    if not m:
        return None
    body = m.group(1).strip()
    if not body or re.fullmatch(r"[（(]\s*(無|none|N/A|pending)\s*[)）]", body, re.I):
        return None
    return body


def classify(text: str) -> tuple[str, str]:
    for key, label, pat in THEMES:
        if pat.search(text):
            return key, label
    return DEFAULT_THEME


def split_entries(body: str) -> list[tuple[str, str, str]]:
    """
    Split a failures section into individual entries.
    Returns [(date, title, body), ...] — falls back to a single ('', '', body)
    if no ### sub-headers exist.
    """
    headers = list(SUB_ENTRY_RE.finditer(body))
    if not headers:
        return [("", "", body.strip())]
    entries = []
    for i, h in enumerate(headers):
        start = h.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        chunk = body[start:end].strip()
        entries.append((h.group("date") or "", h.group("title").strip(), chunk))
    return entries


def gather() -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    if not STM_DIR.exists():
        return grouped
    for stm in sorted(STM_DIR.glob("*.md")):
        if stm.name.startswith("_"):
            continue
        text = stm.read_text(encoding="utf-8")
        body = extract_section(text)
        if not body:
            continue
        ticket = stm.stem
        for entry_date, title, entry_body in split_entries(body):
            key = classify(entry_body or title)
            grouped[key].append({
                "ticket": ticket,
                "date": entry_date.strip(),
                "title": title,
                "body": entry_body,
            })
    return grouped


def render(grouped: dict[tuple[str, str], list[dict]]) -> str:
    today = date.today().isoformat()
    total = sum(len(v) for v in grouped.values())

    out = [
        "---",
        "id: failures",
        "type: ltm",
        "category: technical",
        "status: active",
        "score: 0.0",
        "base_weight: 0.9",
        "urgency: 3",
        f"created: {today}",
        f"updated: {today}",
        "links: []",
        "tags:",
        "- failures",
        "- root-cause",
        "- auto-generated",
        f'summary: Auto-aggregated failure index from {total} entries across STM',
        "---",
        "",
        "# Failure Index",
        "",
        "> 自動生成自 `storage/short_term_memory/*.md` 的 `## Failures` 區段。",
        "> 由 `scripts/extract-failures.py` 維護，手動編輯會被下次 run 覆蓋。",
        f"> Last updated: {today} — total {total} entries",
        "",
        "## Themes",
        "",
    ]
    # ToC
    for (key, label), entries in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        out.append(f"- [{label}](#{key}) — {len(entries)} entries")
    out.append("")
    out.append("---")
    out.append("")

    # Sections
    for (key, label), entries in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        out.append(f"## {label} <a id='{key}'></a>")
        out.append("")
        for e in entries:
            header_bits = [f"**[[{e['ticket']}]]**"]
            if e["date"]:
                header_bits.append(f"`{e['date']}`")
            if e["title"]:
                header_bits.append(e["title"])
            out.append("### " + " — ".join(header_bits))
            out.append("")
            out.append(e["body"])
            out.append("")
        out.append("---")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print to stdout, do not write file")
    args = ap.parse_args()

    grouped = gather()
    rendered = render(grouped)
    if args.print:
        sys.stdout.write(rendered)
        return
    LTM_OUT.parent.mkdir(exist_ok=True)
    LTM_OUT.write_text(rendered, encoding="utf-8")
    total = sum(len(v) for v in grouped.values())
    print(f"Wrote {LTM_OUT.relative_to(ROOT)} — {total} entries across {len(grouped)} themes")


if __name__ == "__main__":
    main()
