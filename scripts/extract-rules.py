#!/usr/bin/env python3
"""
Constitution-style extraction (OmniReflect / Reflexion-inspired).

Scans every STM file for `## User Feedback` and `## Lessons Learned`
sections, pulls out durable rules / preferences expressed there, and
consolidates into `long-term-memory/rules.md` — a single index meant to
be read at the start of every work loop.

Heuristics for what counts as a "rule":
  - Imperative voice (don't / always / never / 要 / 不要 / 必須 / 避免)
  - Explicit Leo correction patterns ("Leo 改成 X" / "Leo 要求 Y" / "Leo 否決 Z")
  - Lines that start with `### 規則 / Rule:` or with bullet "- " containing
    an imperative
Categorization is heuristic and overlap-tolerant; same rule may surface
under more than one category if it touches multiple themes.

Idempotent. Output is auto-generated; do not edit by hand.

Usage:
  python3 scripts/extract-rules.py            # write LTM file
  python3 scripts/extract-rules.py --print    # stdout only
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
LTM_OUT = ROOT / "long-term-memory" / "rules.md"

# Sections to scan for rule-bearing text
RULE_SECTIONS = ("User Feedback", "Lessons Learned", "Decisions Made")

SECTION_RE = lambda hdr: re.compile(
    rf"^##\s+{re.escape(hdr)}\s*$\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL
)

# Imperative-mood signals (EN + zh-TW)
IMPERATIVE = re.compile(
    r"\b(do\s*not|don'?t|never|always|must|avoid|prefer|stop|use|never|require[ds]?)\b"
    r"|\b不要\b|\b必須\b|\b要\b|\b不能\b|\b避免\b|\b禁止\b|\b一律\b|\b總是\b|\b永遠\b|\b應該\b"
    r"|Leo 改成|Leo 要求|Leo 否決|Leo 強調|Leo 偏好|Leo 規則",
    re.IGNORECASE,
)

# Category heuristics (label -> regex)
CATEGORIES: list[tuple[str, str, re.Pattern]] = [
    ("scope-comm",     "Scope / requirement / PM communication",
     re.compile(r"scope|否定|implicit|擴大|PM|requirement|過度|over.engineer", re.I)),
    ("git-workflow",   "Git / branch / commit / push",
     re.compile(r"branch|commit|push|merge|deploy|rebase|reset|build|ship", re.I)),
    ("error-style",    "Error handling / throw / log / silent",
     re.compile(r"throw|catch|silent|log\.warn|報錯|沒.*data.*不.*報錯|fallback", re.I)),
    ("prod-safety",    "Production safety / kafka / email / SFTP",
     re.compile(r"prod\b|kafka|email|SFTP|HL7|生產|fire.and.forget", re.I)),
    ("db-style",       "DB / SQL / FK vs derived column",
     re.compile(r"FK|primary key|column|sql|prisma|migrate|backfill|batch", re.I)),
    ("test-style",     "Testing / mock / verify",
     re.compile(r"mock|jest|spec|verify|integration test|e2e", re.I)),
    ("review-flow",    "Review flow / report format / approval",
     re.compile(r"review|approval|Jira comment|report|format|呈報|確認才", re.I)),
    ("naming-style",   "Naming / variable / API design",
     re.compile(r"name|naming|variable|API design|GraphQL|YAML field|schema field", re.I)),
]
DEFAULT_CATEGORY = ("other", "Other / uncategorized")


def classify(text: str) -> tuple[str, str]:
    for key, label, pat in CATEGORIES:
        if pat.search(text):
            return key, label
    return DEFAULT_CATEGORY


def split_paragraphs(body: str) -> list[str]:
    """Split a markdown section into rule-candidate paragraphs."""
    chunks: list[str] = []
    current: list[str] = []
    for line in body.split("\n"):
        if not line.strip():
            if current:
                chunks.append("\n".join(current).strip())
                current = []
            continue
        if line.startswith("### "):
            if current:
                chunks.append("\n".join(current).strip())
                current = []
            current.append(line)
            continue
        current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]


def is_rule_text(chunk: str) -> bool:
    if not IMPERATIVE.search(chunk):
        return False
    # Skip pure placeholders
    if re.match(r"^[（(]\s*(pending|none|無|N/A)\s*[)）]\s*$", chunk):
        return False
    return True


def gather() -> dict[tuple[str, str], list[dict]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    if not STM_DIR.exists():
        return grouped
    for stm in sorted(STM_DIR.glob("*.md")):
        if stm.name.startswith("_"):
            continue
        text = stm.read_text(encoding="utf-8")
        ticket = stm.stem
        for hdr in RULE_SECTIONS:
            m = SECTION_RE(hdr).search(text)
            if not m:
                continue
            body = m.group(1).strip()
            if not body:
                continue
            for chunk in split_paragraphs(body):
                if not is_rule_text(chunk):
                    continue
                cat = classify(chunk)
                grouped[cat].append({
                    "ticket": ticket,
                    "section": hdr,
                    "text": chunk,
                })
    return grouped


def render(grouped: dict[tuple[str, str], list[dict]]) -> str:
    today = date.today().isoformat()
    total = sum(len(v) for v in grouped.values())

    seen: set[str] = set()
    ordered_links: list[str] = []
    for entries in grouped.values():
        for e in entries:
            if e["ticket"] not in seen:
                seen.add(e["ticket"])
                ordered_links.append(e["ticket"])

    out = [
        "---",
        "id: rules",
        "type: ltm",
        "category: pm_patterns",
        "status: active",
        "score: 0.0",
        "base_weight: 0.8",
        "urgency: 3",
        f"created: {today}",
        f"updated: {today}",
        "links:" if ordered_links else "links: []",
    ]
    if ordered_links:
        out.extend(f"- {t}" for t in ordered_links)
    out += [
        "tags:",
        "- rules",
        "- constitution",
        "- feedback",
        "- auto-generated",
        f"summary: Auto-aggregated constitution from {total} rule-bearing paragraphs across STM",
        "---",
        "",
        "# Rules / Constitution",
        "",
        "> 自動萃取自所有 STM 的 `## User Feedback` / `## Lessons Learned` / `## Decisions Made`",
        "> 段落中含 imperative 語氣或 Leo 明確指令的句子。",
        "> 由 `scripts/extract-rules.py` 維護，下次 run 會覆蓋。",
        f"> Last updated: {today} — total {total} rules across {len(grouped)} categories",
        "",
        "## Categories",
        "",
    ]
    for (key, label), entries in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        out.append(f"- [{label}](#{key}) — {len(entries)} rules")
    out.append("")
    out.append("---")
    out.append("")

    for (key, label), entries in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        out.append(f"## {label} <a id='{key}'></a>")
        out.append("")
        for e in entries:
            out.append(f"### [[{e['ticket']}]] · _{e['section']}_")
            out.append("")
            out.append(e["text"])
            out.append("")
        out.append("---")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()
    grouped = gather()
    rendered = render(grouped)
    if args.print:
        sys.stdout.write(rendered)
        return
    LTM_OUT.parent.mkdir(exist_ok=True)
    LTM_OUT.write_text(rendered, encoding="utf-8")
    total = sum(len(v) for v in grouped.values())
    print(f"Wrote {LTM_OUT.relative_to(ROOT)} — {total} rules across {len(grouped)} categories")


if __name__ == "__main__":
    main()
