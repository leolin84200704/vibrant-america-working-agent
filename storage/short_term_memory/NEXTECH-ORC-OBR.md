---
id: NEXTECH-ORC-OBR
title: emr-v2 parses each OBR once per ORC; partial OBR failure placed silently
category: technical
status: in_review
created: 2026-10-19
updated: 2026-10-19
related: [NEXTECH-EMPTY-ORDER, NEXTECH-onboarding]
---

## Ticket Analysis
### [2026-10-19 21:30]
- Leo: "2 和 3 一起修，開 PR" (follow-ups from NEXTECH-EMPTY-ORDER).
- (2) parser.service.ts OBR + DG1 loops inside per-ORC loop, iterating ALL OBRs -> N ORCs = N classifications per OBR. Prod 7314 (sample 2655460): test_input `2,4,2,4`, original_price 233.88 vs 150. orderItems/total correct.
- (3) Swallowed OBR exception -> remaining OBRs placed, dropped test silent.

## Decisions Made
### [2026-10-19 21:40]
- Move OBR + DG1 out of the ORC loop, run once against final customerInfo (last ORC = placing customer). Block keeps indentation (wrapped in `if (customerInfo)`).
- Any obrParseFailures -> processor holds order, retryable `obr_parse_failed` (same semantics as no_order_items). no_order_items now only for post-OBR item loss; its last_error is bare `no_order_items`.
- Impact scan 90 d: on-prem prod 692 files, 0 multi-ORC, 0 bad OBR-7; AKS prod 7 files, 3 multi-ORC (all NEXTECH).

## Code Changes
### [2026-10-19 21:50]
- Worktree `~/src/lis-backend-emr-v2.worktrees/NEXTECH-ORC-OBR`, branch `bugfix/leo/NEXTECH-ORC-OBR` from main de221a4. PR #488 -> staging, not merged (Leo asked for PR).

## Test Results
### [2026-10-19 21:50]
- 58 suites / 953 passed, build clean, no CJK. Mutation: parser revert -> 2 new tests fail.
- Pending: staging E2E (multi-ORC file + partial failure file) after merge.
