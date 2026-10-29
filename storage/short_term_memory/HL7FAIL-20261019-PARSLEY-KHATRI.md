---
id: HL7FAIL-20261019-PARSLEY-KHATRI
category: emr_integration
created: 2026-10-19
updated: 2026-10-19
status: waiting_external
links: []
score: 0.0806
---

# hl7_file_input 7319 / quarantine 23 - MDHQ Parsley, Kinnari Khatri customer_not_found

## Context
- File order_61716_1791847325_31.hl7, /parsley-la/orders/, MSH.4=17147, ORC.12 NPI 1245490853, patient BELDEN BROOK, 32 OBR, IN1.2=O.
- Diagnosis from DailyJob/hl7_fail/triage_2026-10-14.md: NPI maps in core to 7265/9390/15154/15540/34957/52634; only 52634 is in clinic 17147 (_clinictocustomer). No LIVE+ordering ehr_integrations row for any of them (15540 row disabled 2026-08-21, must stay off: bound to other clinics).

## Progress
### [2026-10-19 10:40]
- Re-verified live: 7319 parse_finished=0 retry_num=0 unchanged; quarantine 23 OPEN; no BELDEN BROOK in lis_core_v7.patient (no duplicate risk).
- Raw file still on on-prem share: /EMR_storage/HL7Message_prod/MDHQ/Prod/Order/order_61716_1791847325_31.hl7 (9520 bytes, //10.0.0.101/storage), checked via kubectl exec on lis-emr-v2-deployment-prod-76558f4df4-m7stv.
- Resolution path on emr-v2 origin/main 270f0b2: customer-detail-fetcher.service.ts:176-302 (core getCustomerByNPINumber -> ehr_integrations LIVE+ordering by customer_id -> filter clinic_id == MSH.4 -> typeRank, updated_at desc).
- Prepared fix (scratchpad fix_7319.py, dry-run passed, rolled back): INSERT mirror of peer cmqa5kvkt00520x9694vs4von (customer 33199, ORDER_ONLY, result_enabled=0) with customer 52634, NPI 1245490853, msh06 17147, requested_by customer_not_found-fix-2026-10-19; then UPDATE hl7_file_input SET retry_num=3 WHERE id=7319 AND parse_finished=0 AND retry_num=0 AND last_error='customer_not_found=KINNARI KHATRI'. In-tx candidates = only the new row.
- NOT committed. Leo chose to send the HL7 to Mingxi first (gate 1b: no written practice/vendor confirmation).
- Correction to earlier reports: quarantine expiry (quarantine-expiry.service.ts, cron 08:20 America/Los_Angeles) only flips quarantined_orders.status to EXPIRED. It does not touch hl7_file_input or the file, so the re-place path stays available after expiry. First sweep past expires_at is 2026-10-20 08:20 PDT.

## Next
- On Mingxi's answer: run fix with --commit (re-check guards), wait for on-prem 15-min rescan, verify core sample on 52634 / 17147, isActive, no duplicate; mark quarantine 23 RESOLVED / CREATED_NEW_PROVIDER (manual, service does not do it).
- Same clinic: 52635, 52761 also lack integrations.
