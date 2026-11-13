---
id: 2026-11-12-vp19079-mdhq-rollback-held-orders
type: journal
date: 2026-11-12
tickets: [VP-19079, MAIL-298885716]
tags: [practice-id, orc-17, mdhq, cerbo, ehr-vendors, prod-db, retry-num]
distilled: true
distilled_on: 2026-11-13
---
# VP-19079: roll MDHQ back to provider-only matching, release 5 held Cerbo orders

Trigger: JJ emailed Cerbo (11-12 03:15Z) the four wrong ORC-17 values and told them we would process the held
orders meanwhile. Leo: "Cerbo先不擋 1,2先做".

Done (runner /tmp/vp19079/rollback.js, prod host asserted, dry-run first):
- ehr_vendors MDHQ id 1 ORC.17 -> NULL, affectedRows 1 at 03:23:13Z; readback THM/FTP ORC.17, NEXTECH MSH.4, count 32.
- hl7_file_input retry_num 0 -> 5 on 7543, 7544, 7546, 7547, 7548 (bound on ids + MDHQ + pf=0 + rn=0), affectedRows 5.
- On-prem rescan at 03:32Z placed all 5 with the historical clinics (5492, 5492, 138167, 13658, 93796),
  samples 2669679-2669683. Re-verified on the read-only account at the Step 5-7 re-run: same state, no new MDHQ rows.
No code, no PR: both are DB rows (policy cached 60 s; rescan every 15 min).

Pitfall: the cloud pod's "HL7 fetch complete ... 0 retry(s) re-enqueued" at 03:30 looked like the rescan skipped the
rows. It only owns 2 folders; MDHQ folders are on the on-prem pod, whose logs are not in Datadog. Check the rows'
last_parse_time instead of the cloud log, and wait a few minutes after the quarter hour.

Next: when Cerbo confirms the four IDs are fixed, propose MDHQ back to ORC.17 (separate ok from Leo).
