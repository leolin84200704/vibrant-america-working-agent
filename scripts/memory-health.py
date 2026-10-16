#!/usr/bin/env python3
"""
Write-stage memory health — the defects the nightly dream cannot repair because
they are absent at write time. Printed into the weekly report; zero API cost.

Checks:
  1. STM files with no `summary:` (index row would be blank / derived)
  2. STM `status: completed` with no Retrospective / Lessons section
  3. Link density (links per file, median incoming) — the 2026-10-15 saturation
     (25% of all pairs linked) silently disabled archiving for five months
  4. LTM files over LTM_LINE_BUDGET lines — defragmentation candidates
  5. STM files eligible for archive under the dream rule (completed, > 30 d, score < 0.1)

Exit code is always 0; this is a report, not a gate.
"""
from __future__ import annotations

import importlib.util
import re
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LTM_LINE_BUDGET = 1500

spec = importlib.util.spec_from_file_location("ms", ROOT / "scripts" / "memory_scoring.py")
ms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ms)  # type: ignore[union-attr]


def main() -> int:
    today = date.today()
    stm = ms.list_tier_files("stm")
    ltm = ms.list_tier_files("ltm")
    metas = {f: ms.read_frontmatter(f) for f in stm + ltm}

    # 1. missing summary
    no_summary = sorted(f.stem for f in stm if not str(metas[f].get("summary") or "").strip())
    print(f"STM without summary: {len(no_summary)}" + (" — " + ", ".join(no_summary) if no_summary else ""))

    # 2. completed without retrospective
    retro_re = re.compile(r"^##+\s*(Retrospective|Lessons)", re.I | re.M)
    no_retro = []
    for f in stm:
        if metas[f].get("status") != "completed":
            continue
        body = f.read_text(encoding="utf-8")
        m = retro_re.search(body)
        filled = bool(m) and len(body[m.end():m.end() + 400].strip()) > 40
        if not filled:
            no_retro.append(f.stem)
    completed = sum(1 for f in stm if metas[f].get("status") == "completed")
    print(f"Completed STM without a filled Retrospective/Lessons: {len(no_retro)} of {completed}")

    # 3. link density
    incoming: dict[str, int] = {}
    total = 0
    for f in stm:
        links = metas[f].get("links") if isinstance(metas[f].get("links"), list) else []
        total += len(links)
        for l in links:
            incoming[str(l)] = incoming.get(str(l), 0) + 1
    inc_vals = [incoming.get(metas[f].get("id", f.stem), 0) for f in stm]
    n = len(stm)
    density = 100.0 * total / (n * (n - 1)) if n > 1 else 0.0
    print(f"STM links: {total} ({density:.1f}% of possible pairs); incoming per file "
          f"median {statistics.median(inc_vals) if inc_vals else 0}, max {max(inc_vals) if inc_vals else 0}")

    # 4. oversized LTM
    big = [(f.stem, sum(1 for _ in f.open(encoding="utf-8"))) for f in ltm]
    big = [(s, c) for s, c in big if c > LTM_LINE_BUDGET]
    print(f"LTM files over {LTM_LINE_BUDGET} lines (defrag candidates): "
          + (", ".join(f"{s} ({c})" for s, c in sorted(big, key=lambda x: -x[1])) if big else "none"))

    # 5. archive-eligible
    eligible = []
    for f in stm:
        meta = metas[f]
        if meta.get("status") != "completed":
            continue
        score, days = ms.score_file(f, meta, incoming.get(meta.get("id", f.stem), 0), today)
        if days > 30 and score < 0.1:
            eligible.append(f.stem)
    print(f"STM eligible for archive on the next dream (completed, >30 d, score<0.1): {len(eligible)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
