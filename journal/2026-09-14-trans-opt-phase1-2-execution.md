---
date: 2026-09-14
slug: trans-opt-phase1-2-execution
tickets: [TRANS-OPT, VP-17348, VP-18152]
---

# Trans optimization: from plan to prod in one session

## What happened
- Misread Leo's "要等最久的一個" as longest lead time (did S1 config repoint) when he meant highest latency; owned it, then pivoted to code fixes.
- Phase 0.2 green baselines for both trans repos (v2 #628 by me, v1 #767 by a subagent I reviewed).
- v2 S2 direct gRPC behind TRANS_PROXY_GRPC_MODE (#629): shadow on prod 121/121 equal, 5-23 ms/call - a nesting removal, not a p95 lever (I had said so; the plan had not).
- Read-only analyses (4 subagents) overturned 3 of 4 plan premises; every code change then followed golden spec -> change -> PR: findPatient #769, createPatient Kafka #773, getTimeLine #774 + #776 (flagged), newrange #775.
- First post-deploy window met or beat every estimate (createPatient 3.56 -> 1.68 s p50; getTimeLine 2.15 -> 1.71 s; kit shadow 16/16 equal, in-process ~0.7 s faster).

## Decisions / corrections from Leo
- "能修的直接修", only trans v1 + v2; no tickets to other teams.
- Test after deploy against my own estimates; record misses as factory lessons.

## Lessons filed (factory PRs #78-#81)
critical-path estimates; re-derive plan premises; golden specs pin failure paths; gates must own their environment.

## Open threads
See STM TODO (business-hours measurement, S2 grpc switch, kit inprocess switch, newrange error rate, cleanups).
