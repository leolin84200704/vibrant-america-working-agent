#!/usr/bin/env python3
"""
Standalone memory scoring + linking + index rebuild.

Replaces the dream pipeline's dependency on the legacy Python service
(src/memory/scorer.py, src/memory/linker.py). Same formula, same output
format, zero imports from src/ — only stdlib + PyYAML.

Formula: score = (base_weight * recency * reference_boost * urgency_boost) / 8.0
  recency         e^(-days_since_update / half_life); STM=30d, archive=180d,
                  LTM fixed at 0.99 (knowledge barely decays)
  reference_boost 1.0 + 0.1 * min(incoming_link_count, LINK_BOOST_CAP)
                  (incoming counted from STM links only; LTM/archive do not vote)
  urgency_boost   1.0 + 0.15 * (urgency - 1), urgency 1-5 from frontmatter

Linking: `links:` on STM files is REBUILT from scratch on every run (not
accumulated; LTM files keep union semantics). Two files link when they share >= MIN_LINK_OVERLAP keywords after
dropping keywords present in more than MAX_KEYWORD_DF of the STM+LTM corpus.
Hand-curated `relations:` targets are always kept in `links:`.

Why (2026-10-15 research+improve): with accumulate-only linking and no document-
frequency filter, 25% of all file pairs were linked (median 99 incoming links per
STM, boost x10). The boost became a near-constant inflation, so completed tickets
never fell under the 0.1 archive threshold: STM grew 45 -> 178 files in five
months and grep retrieval hit@1 fell 0.51 -> 0.11.

Pinning: a file with `score_frozen: true` in frontmatter keeps its stored
`score:` untouched by the formula (add a `note:` explaining why). Use for
files the formula mis-ranks (e.g. an archived reference that must stay hot).

Usage:
  python3 scripts/memory_scoring.py            # link + rescore + rebuild indexes
  python3 scripts/memory_scoring.py --stats    # print stats only, no writes
"""
from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None  # fall back to the minimal flat parser below

AGENT_ROOT = Path(__file__).resolve().parent.parent
TIER_DIRS = {
    "stm": AGENT_ROOT / "storage" / "short_term_memory",
    "ltm": AGENT_ROOT / "long-term-memory",
    "archive": AGENT_ROOT / "archive",
}
TIER_NAMES = {"stm": "Short-Term Memory", "ltm": "Long-Term Memory", "archive": "Archive"}

HALF_LIFE = {"stm": 30, "archive": 180}
LTM_FIXED_RECENCY = 0.99
NORMALIZATION = 8.0
URGENCY_BOOST_PER_LEVEL = 0.15
MIN_LINK_OVERLAP = 3
MAX_KEYWORD_DF = 0.20   # keywords in > 20% of STM+LTM files carry no link signal
LINK_BOOST_CAP = 20     # reference_boost saturates at x3.0

CATEGORY_KEYWORDS = {
    "emr_integration": [
        "emr", "hl7", "ehr", "integration", "provider", "practice",
        "sftp", "bundle", "msh", "obr", "obx", "cerbo", "athena",
        "order_client", "ehr_integration", "result_transmission",
    ],
    "technical": [
        "grpc", "nestjs", "prisma", "typescript", "mysql", "postgresql",
        "kafka", "docker", "api", "controller", "service", "module",
    ],
    "repo_patterns": [
        "build", "deploy", "config", "env", "migration", "script",
        "pattern", "gotcha", "investigation",
    ],
    "pm_patterns": ["ticket", "routing", "pm", "kristine", "sprint", "jira"],
}


def _parse_scalar(raw: str):
    raw = raw.strip()
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')) and len(raw) >= 2:
        return raw[1:-1]
    if raw in ("", "null", "~"):
        return None
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    return raw


def _parse_flat_yaml(text: str) -> dict:
    """Minimal parser for the `key: value` + list frontmatter used in this repo.
    Only used when PyYAML is unavailable.

    Handles BOTH block lists (`tags:` then `- item`) and flow lists (`[a, b]`).
    Block-list support is load-bearing: without it `tags:` parsed to the empty
    string, which silently (a) blanked the Tags column in every _index.md,
    (b) starved auto-linking of its keywords, and (c) made write_frontmatter
    emit `tags:` with no items — destroying the tags of every file it rewrote.
    Tags are retrieval triggers, so that was silent memory loss (2026-08-15).
    Same defect class as the run-regression.py grader parser fixed the same day;
    when fixing a hand-rolled fallback parser, grep for its siblings."""
    meta: dict = {}
    list_key: str | None = None
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        # A block-list item belongs to the most recent bare `key:` line. Checked
        # before the ':' test — an item may itself contain a colon (e.g. a URL).
        if line.lstrip().startswith("- ") and list_key is not None:
            meta.setdefault(list_key, []).append(_parse_scalar(line.lstrip()[2:]))
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip(), raw.strip()
        list_key = None
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            meta[key] = [_parse_scalar(x) for x in inner.split(",")] if inner else []
        elif not raw:
            # Bare `key:` — a block list opens here, or it is genuinely empty.
            # Default to [] and let following `- ` items fill it.
            list_key = key
            meta[key] = []
        else:
            meta[key] = _parse_scalar(raw)
    return meta


def _dump_flat_yaml(meta: dict) -> str:
    lines = []
    for key, val in meta.items():
        if isinstance(val, list):
            # Block list — matches PyYAML's default_flow_style=False output, so
            # the with-/without-PyYAML paths round-trip to the same shape.
            lines.append(f"{key}:")
            lines.extend(f"- {v}" for v in val)
        elif isinstance(val, str) and (":" in val or "#" in val or val != val.strip()):
            escaped = val.replace('"', '\\"')
            lines.append(f'{key}: "{escaped}"')
        else:
            lines.append(f"{key}: {val if val is not None else ''}")
    return "\n".join(lines)


def read_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {}
    try:
        end = content.index("\n---", 3)
    except ValueError:
        return {}
    block = content[4:end]
    if yaml is not None:
        try:
            return yaml.safe_load(block) or {}
        except yaml.YAMLError:
            # Hand-written frontmatter is not always valid YAML (a plain scalar
            # with ': ' inside `summary:` / `unblock_when:` is enough). Returning
            # {} here was catastrophic: reconcile-jira.py and the rescore pass
            # both write `meta` back, so an unreadable file became a file with
            # ONE key. 2026-10-08: VP-18714 and LBS-1828 lost their whole
            # frontmatter that way; SANDBOX-SEED-W2W-20261005 was next in line.
            print(f"warning: {path}: frontmatter is not valid YAML; using lenient parse",
                  file=sys.stderr)
            return _parse_lenient_yaml(block)
    return _parse_flat_yaml(block)


def _parse_lenient_yaml(block: str) -> dict:
    """Entry-by-entry fallback for frontmatter that PyYAML rejects as a whole.

    Each top-level `key:` entry (with its indented continuation lines) is parsed on
    its own; an entry PyYAML still rejects is kept verbatim as one joined plain
    string. Lossless for every key, unlike `_parse_flat_yaml`, which drops
    continuation lines and nested mappings."""
    entries: list[list[str]] = []
    cur: list[str] = []
    for line in block.splitlines():
        if line and not line[0].isspace() and ":" in line and cur:
            entries.append(cur)
            cur = []
        cur.append(line)
    if cur:
        entries.append(cur)
    meta: dict = {}
    for ent in entries:
        text = "\n".join(ent)
        if yaml is not None:
            try:
                parsed = yaml.safe_load(text)
                if isinstance(parsed, dict):
                    meta.update(parsed)
                    continue
            except yaml.YAMLError:
                pass
        key, _, first = ent[0].partition(":")
        parts = [first.strip()] + [l.strip() for l in ent[1:]]
        meta[key.strip()] = " ".join(p for p in parts if p)
    return meta


def write_frontmatter(path: Path, meta: dict) -> None:
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    if content.startswith("---\n"):
        end = content.index("\n---", 3)
        # Guard against the 2026-10-08 failure mode: a caller that could not read
        # the frontmatter must never be allowed to replace it with a stub.
        if "id" not in meta and "id:" in content[4:end]:
            raise ValueError(
                f"refusing to overwrite frontmatter of {path}: new meta has no 'id' "
                f"but the file does (read failure upstream?)"
            )
        # end points at the newline BEFORE the closing '---', so end + 4 lands on the
        # newline that terminates the closing delimiter line. Leaving it in and then
        # writing '---\n' + body re-inserted one blank line on every single write, so
        # STM/LTM bodies grew a blank line per dream run (LBS-1541 reached 106).
        # Strip all leading blank lines and re-emit exactly one separator: idempotent.
        body = content[end + 4:].lstrip("\n")
    else:
        body = content.lstrip("\n")
    if yaml is not None:
        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False).rstrip()
    else:
        yaml_str = _dump_flat_yaml(meta)
    path.write_text(f"---\n{yaml_str}\n---\n\n{body}", encoding="utf-8")


def list_tier_files(tier: str) -> list[Path]:
    d = TIER_DIRS[tier]
    if not d.exists():
        return []
    return [f for f in sorted(d.glob("*.md")) if f.name != "_index.md"]


def to_date(val) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val[:10])
        except ValueError:
            return date.today()
    return date.today()


# ── Linking ──────────────────────────────────────────────────────


def extract_keywords(path: Path, meta: dict) -> set[str]:
    content = path.read_text(encoding="utf-8").lower()
    keywords = set()
    tags = meta.get("tags", [])
    if isinstance(tags, list):
        keywords.update(str(t).lower() for t in tags)
    for kw in CATEGORY_KEYWORDS.get(meta.get("category", ""), []):
        if kw in content:
            keywords.add(kw)
    return keywords


def relation_targets(meta: dict) -> set[str]:
    """Ids named in the hand-curated `relations:` block (any edge type)."""
    rel = meta.get("relations")
    out: set[str] = set()
    if isinstance(rel, dict):
        for v in rel.values():
            if isinstance(v, list):
                out.update(str(x) for x in v)
            elif v:
                out.add(str(v))
    return out


def compute_links(kws: dict[str, set[str]]) -> dict[str, set[str]]:
    """Pairwise keyword-overlap links after dropping high-document-frequency keywords."""
    n = len(kws)
    df: dict[str, int] = {}
    for s in kws.values():
        for k in s:
            df[k] = df.get(k, 0) + 1
    allowed = {k for k, c in df.items() if c <= MAX_KEYWORD_DF * n}
    filtered = {i: s & allowed for i, s in kws.items()}
    links: dict[str, set[str]] = {i: set() for i in kws}
    ids = sorted(kws)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if len(filtered[a] & filtered[b]) >= MIN_LINK_OVERLAP:
                links[a].add(b)
                links[b].add(a)
    return links


def auto_link_all() -> tuple[int, int]:
    """Rebuild `links:` on every STM/LTM file. Returns (files_rewritten, total_links)."""
    files = list_tier_files("stm") + list_tier_files("ltm")
    metas = {f: read_frontmatter(f) for f in files}
    ids = {f: metas[f].get("id", f.stem) for f in files}
    kws = {ids[f]: extract_keywords(f, metas[f]) for f in files}
    path_by_id = {ids[f]: f for f in files}
    links = compute_links(kws)

    rewritten = 0
    total = 0
    for file_id, path in path_by_id.items():
        meta = metas[path]
        old = meta.get("links") if isinstance(meta.get("links"), list) else []
        keep = relation_targets(meta)
        if meta.get("type") == "ltm":
            # LTM links accumulate (union) as before: extract-failures.py /
            # extract-rules.py write their own outbound links into failures.md /
            # rules.md and would otherwise churn against a from-scratch rebuild.
            keep |= {str(x) for x in old}
        new = sorted((links[file_id] | keep) - {file_id})
        total += len(new)
        if sorted(str(x) for x in old) != new:
            meta["links"] = new
            write_frontmatter(path, meta)
            rewritten += 1
    return rewritten, total


# ── Scoring ──────────────────────────────────────────────────────


def score_file(path: Path, meta: dict, incoming: int, today: date) -> tuple[float, int]:
    base_weight = float(meta.get("base_weight", 0.9))
    tier = meta.get("type", "stm")
    days_since = (today - to_date(meta.get("updated", today))).days

    if tier == "ltm":
        recency = LTM_FIXED_RECENCY
    else:
        recency = math.exp(-days_since / HALF_LIFE.get(tier, 30))

    boost = 1.0 + 0.1 * min(incoming, LINK_BOOST_CAP)
    try:
        urgency = max(1, min(5, int(meta.get("urgency", 1))))
    except (TypeError, ValueError):
        urgency = 1
    urgency_boost = 1.0 + URGENCY_BOOST_PER_LEVEL * (urgency - 1)

    return round((base_weight * recency * boost * urgency_boost) / NORMALIZATION, 4), days_since


def rescore_and_reindex(write: bool = True) -> dict:
    today = date.today()
    all_files = [(t, f) for t in TIER_DIRS for f in list_tier_files(t)]
    metas = {f: read_frontmatter(f) for _, f in all_files}

    # Only STM links vote. Archive files keep their historical links but a pile
    # of archived tickets must not keep a long-finished STM looking hot, and LTM
    # link lists accumulate forever (see auto_link_all), so they carry no signal.
    incoming: dict[str, int] = {}
    for tier, f in all_files:
        if tier != "stm":
            continue
        for link in metas[f].get("links", []) if isinstance(metas[f].get("links"), list) else []:
            incoming[link] = incoming.get(link, 0) + 1
    missing_summary: list[str] = []

    stats: dict = {}
    for tier in TIER_DIRS:
        scored = []
        for f in list_tier_files(tier):
            meta = metas[f]
            file_id = meta.get("id", f.stem)
            if str(meta.get("score_frozen", "")).lower() == "true":
                # Pinned against the formula (user/dream intent — e.g. an
                # archived reference the formula over-ranks). Keep the stored
                # score; set score_frozen: true + score: + note: in frontmatter.
                scored.append((float(meta.get("score", 0.0) or 0.0), file_id, meta))
                continue
            score, _ = score_file(f, meta, incoming.get(file_id, 0), today)
            if write and abs(float(meta.get("score", 0.0) or 0.0) - score) > 0.0001:
                meta["score"] = score
                write_frontmatter(f, meta)
            scored.append((score, file_id, meta))
        scored.sort(key=lambda s: s[0], reverse=True)

        if write:
            lines = [
                f"# {TIER_NAMES[tier]} Index",
                "",
                "> Auto-generated by scoring engine. Do not edit manually.",
                f"> Last updated: {today.isoformat()}",
                "",
            ]
            if tier == "archive":
                lines += ["| Score | ID | Summary | Original Tier | Archived |",
                          "|-------|-----|---------|---------------|----------|"]
                for score, file_id, meta in scored:
                    lines.append(f"| {score:.2f} | {file_id} | {meta.get('summary', '')} | "
                                 f"{meta.get('original_tier', 'stm')} | {meta.get('updated', '')} |")
            else:
                lines += ["| Score | ID | Summary | Tags | Status | Category | Updated |",
                          "|-------|-----|---------|------|--------|----------|---------|"]
                for score, file_id, meta in scored:
                    tags = meta.get("tags", [])
                    tag_str = " ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags or "")
                    summary, derived = index_summary(TIER_DIRS[tier] / f"{file_id}.md", meta)
                    if derived:
                        missing_summary.append(file_id)
                    lines.append(f"| {score:.2f} | {file_id} | {summary} | {tag_str} | "
                                 f"{meta.get('status', 'active')} | {meta.get('category', 'technical')} | "
                                 f"{meta.get('updated', '')} |")
            lines.append("")
            (TIER_DIRS[tier] / "_index.md").write_text("\n".join(lines), encoding="utf-8")

        scores = [s[0] for s in scored]
        stats[tier] = {
            "count": len(scores),
            "highest": max(scores) if scores else 0,
            "lowest": min(scores) if scores else 0,
            "median": sorted(scores)[len(scores) // 2] if scores else 0,
        }
    stats["_missing_summary"] = missing_summary
    return stats


_ID_PREFIX = None


def index_summary(path: Path, meta: dict) -> tuple[str, bool]:
    """Summary text for an index row. Falls back to `title:` and then to the first
    H1 of the body, so a file written without `summary:` still routes instead of
    showing a blank cell (16 of 178 STM rows were blank on 2026-10-15).
    Returns (text, derived_from_fallback)."""
    s = str(meta.get("summary") or "").strip()
    if s:
        return " ".join(s.split()), False
    t = str(meta.get("title") or "").strip()
    if t:
        return " ".join(t.split()), True
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return "", True
    for line in body.splitlines():
        if line.startswith("# "):
            head = line[2:].strip()
            fid = str(meta.get("id", path.stem))
            if head.startswith(fid):
                head = head[len(fid):].lstrip(" -—:")
            return head, True
    return "", True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stats", action="store_true", help="print stats only, no writes")
    args = parser.parse_args()

    if args.stats:
        stats = rescore_and_reindex(write=False)
    else:
        rewritten, total = auto_link_all()
        print(f"Links rebuilt: {total} links, {rewritten} files rewritten")
        stats = rescore_and_reindex(write=True)
        print("Scores and indexes rebuilt")

    missing = stats.pop("_missing_summary", [])
    if missing:
        print(f"  WARN: {len(missing)} index rows derived from title/H1 (no summary:): "
              + ", ".join(missing))
    for tier, s in stats.items():
        print(f"  {tier}: count={s['count']} highest={s['highest']:.2f} "
              f"lowest={s['lowest']:.2f} median={s['median']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
