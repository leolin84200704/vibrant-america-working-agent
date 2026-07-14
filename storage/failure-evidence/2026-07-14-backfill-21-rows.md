# 2026-07-14 backfill: 21 historical undiagnosed failure rows (VP-17412 E2E test)

First full run of the agent-layer diagnosis loop (watch v7 Step 5), executed as
a backfill over every `hl7_file_input` row from the last 30 days that had a
failure tag (or exhausted retries) and `error_detail IS NULL`.

Pod-log evidence: NOT available for any of these rows — they all predate the
current replicasets (logs GC'd by redeploys). That gap is exactly what watch
v7 Step 5a now closes for new failures. Diagnoses below are built from DB
ground truth + established investigation records (VP-17120 STM, ghost-process
investigation, FollowThatPatient/VP-17385 records).

## Groups

| Rows | Class | Diagnosis (summary) |
|---|---|---|
| 6358,6359,6374-6376,6388,6397,6399-6401,6405,6407-6409 (14) | RESOLVED, stale tag | VACP149591/149592/126422 owned by cust 4953; NPI 1396844346 dual-LIVE resolved to cust 3057 -> code not found. Fixed 6/19 (3057 integration -> PENDING); orders placed as samples 2581900-2581917 in manual recovery; tags predate clear-on-success fix. |
| 6441,6442 | STRANDED, ghost-era /tmp | Fetched 6/23 into ephemeral /tmp; file lost; retries exhausted; raw HL7 preserved in order_input (recoverable). |
| 6456 | customer_not_found | No usable NPI; name fallback 'ELISSA SILLARS' matched no customer; file persists in /EMR_storage (re-enqueue after config). |
| 6482 | discountpanel289 | Official-bundle id absent/expired in bundle map at parse time; file persists (re-enqueue possible). |
| 6556 | VATEST x6 | Six test codes not orderable at parse time (must exist + isOrderable=true); file persists. |
| 6575 | VASC727501 + file lost | Shortcut absent from Get Shortcuts catalog (clinic 154338/cust 51154 has only 728906-728914) AND ghost-fetched to /tmp (file gone). Needs vendor catalog fix + resend. |
| 6590 | ghost fetch, exhausted | Ghost-fetched 7/13 to /tmp; legit pod couldn't read; retries burned in 40 min; raw HL7 in order_input; rescue plan pending Leo approval. |

## DB write record
Per-row bounded UPDATEs (`WHERE id=<id> AND error_detail IS NULL`), app account,
2026-07-14. Full SQL preserved in the session scratchpad; the exact English
text written per row is reproduced in the UPDATE statements.
