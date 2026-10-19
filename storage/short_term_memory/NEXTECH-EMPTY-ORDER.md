---
id: NEXTECH-EMPTY-ORDER
title: emr-v2 places HL7 orders with zero items when every OBR throws (Nextech date-only OBR-7)
category: technical
status: in_review
created: 2026-10-19
updated: 2026-10-19
related: [NEXTECH-onboarding]
---

## Ticket Analysis
### [2026-10-19 11:50]
- No Jira ticket; Leo asked directly ("both fixes, open a branch"). Cases: hl7_file_input 7251 (sample 2646314) and 7314 (sample 2650711), both NEXTECH, OBR-7 date-only (`20261002`, `20261009`).
- Cause chain: `obr-parser.service.ts` passes OBR-7 straight to `isICD9`, whose regex requires exactly 12 digits -> throws -> `parser.service.ts` OBR loop catch logs `OBR parse failed` and continues -> errorCodes empty -> order assembled with `orderItems: []` -> processor places it.

## Decisions Made
### [2026-10-19 12:20]
- Fix 1: `normalizeObr7` accepts HL7 TS precisions 8/10/12/14 digits (+ optional .ffff and +/-ZZZZ), truncates/pads to 12 (missing time -> 00:00, tz ignored). Anything else returned unchanged so isICD9 still throws. 12-digit input is byte-identical to before.
- Fix 2: processor refuses to call finalize when `orderFrontend.orderItems` is empty. Chose RETRYABLE (`markFailure`, class `no_order_items`) over terminal: items can also vanish downstream of OBR parsing (BestDeal leftover id missing from mapping cache -> `continue`), and a deployed parser fix re-places rows still holding retries. last_error = `no_order_items (skipped OBR-1: ...; OBR-2: ...)` via new `obrParseFailures` on the parse result.
- Not done (asked Leo): partial drop (one of N OBRs throws, the rest place) is still silent.

## Code Changes
### [2026-10-19 12:40]
- Worktree `~/src/lis-backend-emr-v2.worktrees/NEXTECH-EMPTY-ORDER`, branch `bugfix/leo/NEXTECH-EMPTY-ORDER` from origin/main 270f0b2.

### [2026-10-19 13:00]
- Committed + pushed; PR #486 -> staging (Vibrant-America/lis-backend-emr-v2). Not merged yet: Leo asked for the PR only; open question on partial-OBR drop still pending.

## Test Results
### [2026-10-19 12:45]
- hl7-order-processing + hl7: 58 suites / 948 passed. nest build clean. No CJK.
- Mutation: reverting the normalizeObr7 call makes 2 new tests fail.
- Real files: new dist ObrParserService on both archived prod files -> all 4 OBRs classify testGroup, collection time `10/02/2026 00:00` / `10/09/2026 00:00`.
- Prod package_price_mapping: VAREQUISTION35/36/106 = ids 2/4/21, isOrderable TRUE. VAREQ groups do place in prod (BIOINSIGHTS 7196 placed with items).

### [2026-10-19 19:20] Staging E2E PASSED (PR #486 merged by Leo 18:50Z, staging f727216)
- Deploy: AKS staging `5686bb7f5b-njgpm` + on-prem staging intake `lis-emr-v2-deployment-7c889846b8-vg9n8` (ns default, via appserver04 expect/ssh) both on f727216; dist grep normalizeObr7=2, NO_ORDER_ITEMS_CLASS=3.
- Before-evidence: staging 2245 (VP17827 T1, 10-08) had 14-digit OBR-7 and was placed EMPTY (sample 2554429, orderItems []) -- same bug, nobody noticed.
- Fixture: T1 clone (FOLLOWTHATPATIENT, provider 4769 @ practice 134410), OBR-4 VAREQUISTION36 + VAREQUISTION106, only OBR-7 / MSH-10 varied. Files in on-prem `/EMR_storage/HL7Message_prod/FOLLOWTHATPATIENT/Staging/Order/`, rows retry_num 2, rescan 19:15Z.
  - 2247 N1 OBR-7 `20261019`: placed sample 2554939, items [4, 21], emr_sample.test_input `4,21`, sample_collection_time 2026-10-19 00:00.
  - 2248 N2 OBR-7 `20261019195515`: placed sample 2554940, items [4, 21], collection 19:55.
  - 2249 N3 OBR-7 `2026-10-19`: NOT placed; last_error `no_order_items (skipped OBR-1: Invalid sampleCollectionTime format...; OBR-2: ...)`, retry_num 2->1, parse_finished 0, emr_code_not_found NULL. Pod log shows both `OBR parse failed` + `parse failure (retry_num→1): no_order_items`.
- Cleanup: 2249 set parse_finished=1 retry_num=0 by id+file_name+parse_finished=0 (1 row) before the 19:30Z tick could exhaust it and fire Slack. Staging samples 2554939/2554940 are dev-core samples (ids collide with prod snapshot) -- left in place, same as VP-17827.
- Next: release PR staging -> main is Leo's.

### [2026-10-19 19:30] Release PR #487 staging -> main opened (2 commits, = #486). Leo merges; after merge verify prod pods on main HEAD + dist grep, then watch next NEXTECH order.
