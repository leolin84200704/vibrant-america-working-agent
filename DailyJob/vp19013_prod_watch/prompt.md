You are running as a scheduled job: the VP-19013 prod watch. Everything you do
is READ-ONLY on prod. Never cancel, re-place or modify an order, never write to
any DB, never post to Jira or Slack, never transition a ticket.

Background. lis-backend-emr-v2 (release #530, prod since 2026-11-04, commit
099ca3b or later) swaps a male patient's Foundation Zoomer 2.0 (pricing package
868, EMR code VAREQUISTION486) and Foundation Baseline (869, VAREQUISTION487)
to their male PSA twins 876 / 877 before placing an HL7 order. The swap runs
only on the Place Order API path (env HL7_ORDER_PLACEMENT_MODE unset) and only
when the twin id is in emr-v2's pricing catalog cache (refreshed every 30 min).
Pricing (Ray) was expected to create 876/877 in prod at the 2026-11-09 release.
Male = raw PID-8 'M'/male; female or blank PID-8 must stay on 868/869.
Code: ~/src/lis-backend-emr-v2 origin/main,
src/modules/hl7-order-processing/services/gender-variant.ts and
order-finalizer.service.ts (log lines at ~:298 and ~:465):
  `[VP-19013] male patient: package 868 -> male variant 876`
  `[VP-19013] male patient: bundle <id> member 868 -> male variant 876`
Full history and the staging E2E method: storage/short_term_memory/VP-19013.md
(read it first). EMR / hl7_file_input know-how: long-term-memory/emr-integration.md.
Datadog service: `service:lis-emr-v2-deployment-prod`.

State: DailyJob/vp19013_prod_watch/state.json. Only look at orders processed
after `checked_through_utc`; skip anything already in `orders_checked`.

STEP 0 - sync. git fetch / status on this repo (main) and on
~/src/lis-backend-emr-v2 (main). Confirm prod still runs code containing the
swap (Datadog pod/version or the dist check used in the STM).

STEP 1 - twins live? Determine whether 876/877 now exist in prod pricing
(any evidence: emr-v2 cache/catalog logs, the pricing service, a swap log line).
Record it in `twins_seen_in_prod` (timestamp of first evidence, or null).

STEP 2 - find candidate orders since `checked_through_utc`:
  a) Datadog: `service:lis-emr-v2-deployment-prod "[VP-19013]"`.
  b) Independently, prod HL7 orders containing VAREQUISTION486 / VAREQUISTION487
     (or a bundle whose members include 868/869), with the patient's PID-8.
     Use whatever read-only path the STM / LTM documents for prod hl7_file_input.
     Positive control: the same query shape must return the expected count of
     ordinary HL7 orders in the window; if it returns nothing, the query is
     broken -> REPORT-ONLY.

STEP 3 - judge each candidate:
  - PASS: male PID-8, twins live, swap log line present, and the placed order's
    package readback (order service package-tests for the sample, as in the STM
    staging E2E: 876 -> package 492, 877 -> package 493) shows the male package.
  - FAIL: male PID-8, twins already live before the order was processed, but no
    swap log or the placed package is not the male one. Also FAIL: a female or
    blank-PID-8 order that got swapped.
  - EXPECTED-FALLBACK: male order processed before the twins were live -> base
    id is correct; record it, not a pass.
  - NOT-APPLICABLE: female/blank orders correctly left on 868/869 (record them;
    one of these is useful evidence too).

STEP 4 - write `DailyJob/vp19013_prod_watch/report_<YYYY-MM-DD>.md` (Traditional
Chinese, URLs surrounded by spaces), appending if today's file exists: twins
status, control count, every candidate with hl7_file_input id, sample/accession,
PID-8, log line (or its absence), placed package, verdict. Update state.json
(`checked_through_utc` = now, `orders_checked`, `twins_seen_in_prod`).

STEP 5 - decide:
  - First PASS -> set `verified_order` and `status: "done"`. Also draft (do NOT
    post) the Jira Dev Complete comment for VP-19013 and the QH-7936 QA
    verification comment (English, Implementation / Verification / Residual) in
    the report so Leo can review them.
  - Any FAIL -> keep watching, notify with "FAIL" in the text.
  - FINAL_RUN=1 -> summarise the whole window and set `status: "done"`.

Commit only state.json and the report to this repo's main and push (git pull
--rebase first; never force). Then one osascript notification:
`osascript -e 'display notification "<one line>" with title "VP-19013 prod watch"'`
Notify on PASS, FAIL, FINAL, REPORT-ONLY, and the first time twins are seen
live; stay silent on a run that found nothing new.

REPORT-ONLY path: if a tool or query is broken or the evidence is inconclusive,
write that in the report, commit, notify, and do not change `status`.
