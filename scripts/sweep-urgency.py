#!/usr/bin/env python3
"""
Sweep STM frontmatter and add `urgency:` field based on simple rules:
  - id starts with 'INCIDENT-'                                 → 5
  - tags include 'incident' / 'Recurring incident' / 'jira_escalated' → 4
  - id starts with 'LBS-' (Zendesk service desk → prod hotfix) → 3
  - id starts with 'PO-' (System Problem from prod customer)   → 3
  - status == 'resolved' and category == 'technical'           → 2

Default urgency is 1 (no boost). Files already specifying `urgency:`
are left unchanged so manual overrides win.

Idempotent — re-running produces no changes if rules already applied.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STM_DIR = ROOT / "storage" / "short_term_memory"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
URGENCY_LINE_RE = re.compile(r"^urgency:\s*\d+\s*$", re.MULTILINE)
BASE_WEIGHT_LINE_RE = re.compile(r"^(base_weight:\s*[\d.]+)\s*$", re.MULTILINE)


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, list[str] | str] = {}
    body = m.group(1)
    current_list_key: str | None = None
    for line in body.split("\n"):
        if line.startswith("- ") and current_list_key:
            out.setdefault(current_list_key, []).append(line[2:].strip())
            continue
        if ":" in line and not line.startswith(" "):
            current_list_key = None
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                # entering a list
                current_list_key = key
                out.setdefault(key, [])
            else:
                out[key] = value
    return out


def derive_urgency(fm: dict, file_id: str) -> int:
    if file_id.startswith("INCIDENT-"):
        return 5
    tags = [t.lower() for t in fm.get("tags", [])] if isinstance(fm.get("tags"), list) else []
    if any(t in tags for t in ("incident", "recurring incident", "jira_escalated", "ghost-pending")):
        return 4
    if file_id.startswith("LBS-") or file_id.startswith("PO-"):
        return 3
    if fm.get("status") == "resolved" and fm.get("category") == "technical":
        return 2
    return 1


def main() -> None:
    changed = 0
    skipped = 0
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for stm in sorted(STM_DIR.glob("*.md")):
        if stm.name.startswith("_"):
            continue
        text = stm.read_text(encoding="utf-8")
        if URGENCY_LINE_RE.search(text):
            skipped += 1
            # Still record the count
            m = URGENCY_LINE_RE.search(text)
            if m:
                counts[int(re.search(r"\d+", m.group()).group())] += 1
            continue
        fm = parse_frontmatter(text)
        urgency = derive_urgency(fm, stm.stem)
        counts[urgency] += 1
        if urgency == 1:
            # No need to write urgency=1 since it's the default.
            continue
        # Insert `urgency: N` right after the base_weight line.
        m = BASE_WEIGHT_LINE_RE.search(text)
        if not m:
            continue
        new_text = text[: m.end()] + f"\nurgency: {urgency}" + text[m.end():]
        stm.write_text(new_text, encoding="utf-8")
        changed += 1
        print(f"  {stm.stem}: urgency={urgency}")
    print()
    print(f"Sweep done. Changed: {changed}, already-set/skipped: {skipped}")
    print(f"Urgency distribution: {counts}")


if __name__ == "__main__":
    main()
