#!/usr/bin/env python3
"""
Eval baseline script — quantifies dream / scoring state at a point in time.

Used to compare before/after when tuning the scoring engine or dream pipeline.

Outputs (stdout, also writes JSON to eval-output/<date>-<label>.json):
  - Score statistics per tier (count, highest, lowest, median, mean)
  - Per-category counts and score distribution
  - Memory totals (STM/LTM/Archive file counts, total cross-links)
  - LTM file sizes (lines)
  - Operation counts (last dream log: Extracted / Merged / Updated / Promoted / Archived)
  - Coverage signals (% STM with Retrospective filled, % STM with Failures filled)

Usage:
  python scripts/eval.py                       # print to stdout
  python scripts/eval.py --label baseline      # also write to eval-output/<date>-baseline.json
  python scripts/eval.py --diff baseline       # diff current vs baseline
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.memory.manager import MemoryManager  # noqa: E402
from src.memory.scorer import MemoryScorer  # noqa: E402

EVAL_OUT = ROOT / "eval-output"
EVAL_OUT.mkdir(exist_ok=True)


def _section_filled(text: str, header: str) -> bool:
    """Return True if the named markdown section has non-trivial body content."""
    pattern = re.compile(
        rf"^##\s+{re.escape(header)}\s*$\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return False
    body = m.group(1).strip()
    if not body:
        return False
    # Strip "（pending）" "(pending)" "（無）" / "(none)" placeholder lines.
    stripped = re.sub(r"[（(]\s*(pending|none|no|N/A|無)\s*[)）]", "", body, flags=re.I).strip()
    return len(stripped) > 10


def _parse_last_dream_log() -> dict:
    logs = sorted((ROOT / "logs").glob("dream-*.md"))
    if not logs:
        return {}
    text = logs[-1].read_text(encoding="utf-8")
    ops: dict[str, int] = {}
    for op in ("Extracted", "Merged", "Updated", "Promoted", "Archived", "Forgotten"):
        m = re.search(rf"-\s+{op}:\s+(\d+)", text)
        if m:
            ops[op.lower()] = int(m.group(1))
    return {"log": logs[-1].name, "ops": ops}


def collect() -> dict:
    mgr = MemoryManager()
    scorer = MemoryScorer(mgr)
    today = date.today()
    scored = scorer.score_all(today)

    result: dict = {"date": today.isoformat(), "tiers": {}}

    for tier, items in scored.items():
        if not items:
            result["tiers"][tier] = {"count": 0}
            continue
        scores = [s.score for s in items]
        cats = Counter(s.category for s in items)
        result["tiers"][tier] = {
            "count": len(items),
            "highest": round(max(scores), 4),
            "lowest": round(min(scores), 4),
            "median": round(statistics.median(scores), 4),
            "mean": round(statistics.mean(scores), 4),
            "stdev": round(statistics.pstdev(scores), 4) if len(scores) > 1 else 0.0,
            "by_category": dict(cats),
            "archive_candidates": sum(1 for s in items if s.should_archive),
        }

    # Cross-links
    all_files = (
        mgr.list_tier_files("stm")
        + mgr.list_tier_files("ltm")
        + mgr.list_tier_files("archive")
    )
    total_links = 0
    for f in all_files:
        meta = mgr.read_frontmatter(f)
        total_links += len(meta.get("links", []) or [])
    result["cross_links"] = total_links

    # LTM file line counts
    ltm_lines: dict[str, int] = {}
    for f in mgr.list_tier_files("ltm"):
        ltm_lines[f.stem] = sum(1 for _ in f.open(encoding="utf-8"))
    result["ltm_lines"] = ltm_lines

    # Coverage: % STM with Retrospective / Failures sections filled
    stm_files = mgr.list_tier_files("stm")
    n = len(stm_files) or 1
    with_retro = 0
    with_failures = 0
    completed_without_retro = []
    for f in stm_files:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        meta = mgr.read_frontmatter(f)
        retro_ok = _section_filled(text, "Retrospective")
        fail_ok = _section_filled(text, "Failures")
        if retro_ok:
            with_retro += 1
        if fail_ok:
            with_failures += 1
        if meta.get("status") == "completed" and not retro_ok:
            completed_without_retro.append(meta.get("id", f.stem))
    result["coverage"] = {
        "retrospective_pct": round(100 * with_retro / n, 1),
        "failures_pct": round(100 * with_failures / n, 1),
        "completed_without_retro": completed_without_retro,
    }

    result["last_dream"] = _parse_last_dream_log()

    return result


def _flatten(obj, prefix=""):
    """Flatten nested dict for diff display."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        out[prefix] = obj
    else:
        out[prefix] = obj
    return out


def diff(curr: dict, baseline: dict) -> list[str]:
    cf = _flatten(curr)
    bf = _flatten(baseline)
    keys = sorted(set(cf) | set(bf))
    lines = []
    for k in keys:
        a = bf.get(k)
        b = cf.get(k)
        if a == b:
            continue
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            delta = b - a
            sign = "+" if delta >= 0 else ""
            lines.append(f"  {k}: {a} -> {b} ({sign}{round(delta, 4)})")
        else:
            lines.append(f"  {k}: {a} -> {b}")
    return lines


def print_report(r: dict) -> None:
    print(f"# Eval Report — {r['date']}")
    print()
    print("## Scoring (per tier)")
    for tier, s in r["tiers"].items():
        if s.get("count", 0) == 0:
            print(f"- **{tier.upper()}**: empty")
            continue
        print(
            f"- **{tier.upper()}** (n={s['count']}): "
            f"highest={s['highest']}, mean={s['mean']}, median={s['median']}, "
            f"stdev={s['stdev']}, lowest={s['lowest']}, archive_candidates={s['archive_candidates']}"
        )
        cats = ", ".join(f"{c}={n}" for c, n in sorted(s["by_category"].items()))
        print(f"  - categories: {cats}")

    print()
    print("## Memory Totals")
    print(f"- Cross-links: {r['cross_links']}")
    for name, lines in r["ltm_lines"].items():
        print(f"- LTM {name}.md: {lines} lines")

    print()
    print("## Coverage Signals (STM)")
    c = r["coverage"]
    print(f"- Retrospective filled: {c['retrospective_pct']}%")
    print(f"- Failures filled: {c['failures_pct']}%")
    if c["completed_without_retro"]:
        print(f"- Completed but missing Retrospective: {len(c['completed_without_retro'])}")
        for tid in c["completed_without_retro"]:
            print(f"    - {tid}")

    print()
    print("## Last Dream Ops")
    ld = r.get("last_dream", {})
    if ld.get("ops"):
        for op, count in ld["ops"].items():
            print(f"- {op}: {count}")
    else:
        print("- (no dream log parsed)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", help="save snapshot as eval-output/<date>-<label>.json")
    ap.add_argument(
        "--diff",
        metavar="LABEL_OR_PATH",
        help="diff current state against a saved snapshot",
    )
    args = ap.parse_args()

    current = collect()
    print_report(current)

    if args.label:
        out_path = EVAL_OUT / f"{current['date']}-{args.label}.json"
        out_path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\n→ Saved snapshot: {out_path}")

    if args.diff:
        target = Path(args.diff)
        if not target.exists():
            matches = sorted(EVAL_OUT.glob(f"*-{args.diff}.json"))
            if not matches:
                print(f"\n[diff] No snapshot found matching '{args.diff}'", file=sys.stderr)
                sys.exit(2)
            target = matches[-1]
        baseline = json.loads(target.read_text(encoding="utf-8"))
        print(f"\n## Diff vs {target.name}")
        lines = diff(current, baseline)
        if not lines:
            print("- (no changes)")
        else:
            for line in lines:
                print(line)


if __name__ == "__main__":
    main()
