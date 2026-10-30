---
id: NEXTECH-ORC-OBR
title: emr-v2 parses each OBR once per ORC; partial OBR failure placed silently
category: technical
status: done
created: 2026-10-19
updated: 2026-10-19
related:
- NEXTECH-EMPTY-ORDER
- NEXTECH-onboarding
score: 0.078
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

### [2026-10-19 22:05] Staging E2E PASSED + release PR #489
- #488 merged by Leo -> staging 7afa278; on-prem staging `lis-emr-v2-deployment-66f678b4-b8z2k` + AKS staging on 7afa278; dist grep OBR_PARSE_FAILED_CLASS=2.
- Files (on-prem `/EMR_storage/HL7Message_prod/FOLLOWTHATPATIENT/Staging/Order/`, ORC/OBR/DG1 x2, VAREQUISTION35+36, 4769@134410), rescan 22:00Z:
  - 2250 M1 (both OBR-7 date-only): placed sample 2554943, items [2,4], emr_sample.test_input `2,4`, original_price 150 (prod 7314 same codes: `2,4,2,4` / 233.88).
  - 2251 M2 (OBR-2 `2026-10-19`): not placed, last_error `obr_parse_failed (skipped OBR-2: ...)` once, retry 2->1. Cleanup: parse_finished=1 retry_num=0 (1 row, id+file_name+parse_finished=0).
- Release PR #489 staging -> main opened. Leo merges; then verify prod pods on main HEAD + dist grep.

### [2026-10-19 22:30] Released. #489 merged (main 2c077ff). Prod AKS `lis-emr-v2-deployment-prod-55d86c6f4d-gd8p9` and on-prem `lis-emr-v2-deployment-prod-96d489c8f-2c9v7` both on 2c077ff, old pods gone, dist grep OBR_PARSE_FAILED_CLASS=2 on both. Next Nextech order should show single test_input and correct original_price. Open: void empty samples 2650711 / 2646314 (ops).
