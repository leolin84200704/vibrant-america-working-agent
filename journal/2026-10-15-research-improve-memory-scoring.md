---
date: 2026-10-15
slug: research-improve-memory-scoring
related_tickets: [AGENT-IMPROVE-20261015]
distilled: false
---

# Research + improve pass (first since 2026-05-20): link saturation disabled archiving; dream down on spend limit

## Context
Leo: "請進行很久沒有進行的research + improve". The routine was defined 2026-05-20
(review architecture, survey recent agent-memory work, adjust, run the scoring
eval, improve; weekly on Sunday). The weekly launchd job was never loaded, so
the 05-20 run was the only one. Ran it manually today (`logs/weekly-2026-10-15.md`).

## What we explored
- **Dream pipeline down since 10-14 18:30**: four firings, twelve attempts, all
  "You've hit your monthly spend limit" on fable. Interactive fable/opus/sonnet
  `claude -p` all answered at 16:50, so the limit had lifted; the runner still
  retried the same refusal three times in 90 s with no model fallback.
- **Link saturation (root cause of three regressions)**: `memory_scoring.py`
  auto-links accumulate forever and use no document-frequency filter; `sftp`,
  `emr`, `integration`, `hl7`, `practice` appear in >50% of files. 25% of all
  pairs linked, median 99 incoming per STM, reference_boost x10 as a constant.
  Consequences: (1) 56 completed STMs older than 30 d, 1 under the 0.1 archive
  threshold, STM 45 -> 178 since May; (2) grep retrieval hit@1 0.51 -> 0.11;
  (3) the index top 15 was 10 completed tickets held up by link count.
- Simulated DF thresholds: maxdf 20% + overlap 3 gives 634 links (median
  incoming 1, max 26); 10% isolates 133 files. Chose 20%.
- Ruled out IDF-weighted scoring and embeddings: the survey found 11 production
  coding harnesses use no embedding retrieval (arXiv 2609.00006) and
  LongMemEval-V2 grep-over-files beat RAG 72.5 vs 48.5; the fix is index
  write quality, not a vector store.
- 16 STM rows had a blank summary (12 wrote `title:` instead, 4 had neither).
  Retrieval test corpus silently skipped them.
- Retrospective coverage 77.8% -> 26.4%: `reconcile-jira.py` flips status to
  completed on Jira Done with no retrospective written. Not fixed today;
  surfaced in the weekly report.
- `rules.md` (weekly "constitution", now 1294 lines) has no consumer anywhere.
- Factory `REGRESSION.md` describes `eval-tasks/` + `run-regression.py`; the
  runner exists in the factory but this instance has no task bank.
- External survey (subagent, 10 papers + 8 products, May-Oct 2026) in the
  weekly report Notes. Most actionable: skill/lesson admission gate with
  evidence (SkillGLoW, Anthropic dreaming talk, Gemini CLI inbox), typed
  supersedes/expiry on memory (PAST-Bench), hard size caps instead of soft
  decay (Hermes, Claude Code auto-memory), outcome-based replay evals.

## Decisions
- PR `feature/leo/agent-improve-2026-10` (scripts only): DF-filtered idempotent
  STM links, LTM union semantics (extract-failures/extract-rules churn), only
  STM links vote, boost cap x3, index summary fallback + WARN, dream
  spend-limit fallback to opus, weekly write-stage health section.
  Memory regeneration deferred to main after merge (174 STM files rewritten).
- Direct to main: weekly snapshot commit, 16 summaries filled.
- Left for Leo: load the weekly launchd job or not; keep the opus fallback;
  retire rules.md; whether to seed a 20-task regression bank.

## Files touched
scripts/memory_scoring.py, scripts/memory-health.py (new), scripts/run-dream.sh,
scripts/weekly-routine.sh, README.md (PR); storage/short_term_memory/* (16
summaries), logs/weekly-2026-10-15.md, eval-output/* (main).

## Open questions / followups
- After merge: `python3 scripts/memory_scoring.py` on main, commit; first dream
  will archive ~55 completed STMs.
- Retrospective gap: 40 of 108 completed STMs by the new check (72 by eval.py's
  looser one). Mechanism candidate: reconcile-jira flip inserts a
  `### Retrospective (pending)` stub and the daily digest lists them.
- Retrieval test counts raw term hits, so short QH twin summaries lose to the
  long VP summary they mirror (27 of 177 misses, mostly QH-*). Normalise by
  summary length or drop QH twins from the corpus.
- Regression bank per factory REGRESSION.md: 20 recall tasks from STM Failures.

## User feedback this session
None yet (report pending).
