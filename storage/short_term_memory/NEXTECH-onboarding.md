---
id: NEXTECH-onboarding
type: stm
category: emr_integration
status: active
score: 0.2339
base_weight: 1.0
created: 2026-09-22
updated: 2026-10-27
links:
- BIOINSIGHTS-onboarding
- INCIDENT-2604156666
- LBS-1833
- VP-18194
- VP-18372
- VP-18824
- VP-18833
- VP-19008
- VP-19023
- VP-19079
- emr-integration
relations:
  unblocked_by: []
  blocks: []
  sibling:
  - BIOINSIGHTS-onboarding
unblock_when: End-to-end test order from Nextech; test = a .hl7 lands in /965721.Vibrant/Export/,
  gets a sample_id in hl7_file_input under customer 28981, and the result PDF+HL7
  land in /965721.Vibrant/Import/. First provider is LIVE since 2026-09-24, so a file
  arriving now WILL place an order.
tags:
- vp-18336
- qh-7179
- nextech
- atca
- sftp
- vendor-onboarding
- alzheimers-treatment-centers
- ehr-integrations
- george-moricz
- customer-28981
summary: 'New EMR vendor Nextech (bi-directional, for Alzheimer''s Treatment Centers
  of America) — vendor-hosted password SFTP (GoAnywhere) interface02.nextechapp.com:22.
  2026-09-22 connectivity fully verified from local (auth, ls, put/get/remove in Import,
  mkdir+rename archive flow in Export) and AKS prod pod egress OK. Prod INSERTed:
  ehr_vendors id=47 NEXTECH (is_public=0), sftp_folder_mapping id=288 /965721.Vibrant/Export/
  -> /NEXTECH/Prod/Order/ pipeline_location=cloud, ehr_vendor_sftp_templates id=33.
  FIRST ehr_integrations row added 2026-09-24 (id cmufvrntc0000dq0x51sbd986, customer
  28981 George Moricz MD NPI 1215931902, clinic 20834, FULL_INTEGRATION, LIVE) — order
  routing for that NPI now resolves to 28981 and results push to /965721.Vibrant/Import/.
  Still no sample HL7 seen from Nextech. VP-18336 Done 2026-09-22 (vendor build-out);
  QA twin QH-7179 still To Do.'
---

# NEXTECH-onboarding - Work Loop Record

## Ticket Analysis
### [2026-09-22 10:30]
- Source: email thread "Alzheimer's Treatment Centers of America | Vibrant Wellness Nextech Bi-Directional Integration Purchase". Nextech contact: Jessica Marshall (Senior Technical Implementation Specialist, j.marshall@nextech.com, 937-395-7319); CC Carisa Trimmer, Jordan Skeens, Rachel Tomaiolo (Nextech); Xiaoye Li, Britney Little, Jason Thai, Javier Alvarez, Keith (Vibrant side).
- Connectivity = SFTP hosted by Nextech (GoAnywhere 7.10.2): host `interface02.nextechapp.com`, port 22, user `Vibrant.965721@nextechapp.com`, password auth (32 chars, stored ONLY in prod `ehr_vendors.sftp_password`; not in any repo/STM).
- Email labels "Export - Orders" / "Import - Results" are labels, NOT folder names. Real paths: `/965721.Vibrant/Export/` (Nextech exports orders here; we pick up) and `/965721.Vibrant/Import/` (we drop results here; Nextech imports). Both empty on 2026-09-22.
- Leo instruction: 把連接建立好 (set up the connection).
- Jira: zero hits for "Nextech" / "Alzheimer" before 2026-09-22. Ticket created 2026-09-22 on Leo's request: **VP-18336** (Task, P2, assignee Leo, Dev To Do) https://vibrantamerica.atlassian.net/browse/VP-18336 . Created via Atlassian MCP; the vibrant MCP `create_jira_issue` returned 403 (no create permission on VP).

### [2026-09-24 11:20]
- Leo forwarded the same email thread with Jessica Marshall's reply supplying the provider: **George Moricz, NPI 1215931902**. That is `lis_core_v7.customer` 28981 (George Moricz MD, isActive=1, order_placement_allowed=1) — exact NPI match.
- Leo's instruction named the vendor as "MDHQ", which contradicted the thread (Nextech throughout, Jessica is Nextech staff). Raised it rather than executing; Leo confirmed it was a slip. **The DB settled it**: `ehr_vendors` 47 NEXTECH was created 2026-09-22 by Leo with template + folder mapping already in place, while MDHQ was missing nothing. A vendor that has just been provisioned and has zero integrations is the one being onboarded.
- Practice name still unreconciled: the thread's subject says *Alzheimer's Treatment Centers of America*, but no such clinic exists in `lis_core_v7.clinic` (nearest is unrelated "Cancer Treatment Centers of America" 26558). Customer 28981 maps to 3 clinics only: 20834 Naples Center for Functional Medicine, 128573 (same name, no account), 128572 George Moricz_NPI. Leo chose **20834**. The practice-info in the thread is an image and was not readable.

### [2026-10-07 18:10] First Nextech test order — placed EMPTY (no tests), root cause OBR-7 format
- Terry relayed: Nextech tester sent a test order Friday, "failed"; file `NXHL7Exp 26-0012 - 2`, provider George Moricz NPI 1215931902.
- Found: `hl7_file_input` id **7251**, `/965721.Vibrant/Export/NXHL7Exp 26-0012 - 2.hl7`, received 2026-10-02 23:00:07Z, processed 23:00:13Z by pod `lis-emr-v2-deployment-prod-7ff9855688-zvwwx`, `parse_finished=1`, `emr_code_not_found=NULL`, `customer_not_found=NULL`, `last_error=NULL`. Raw file still in SFTP `/965721.Vibrant/Export/archive/` (2340 bytes, CR-delimited, MSH-10 `NxMsg1`, ORM^O01 v2.5.1).
- Routing worked: customer 28981 / clinic 20834 resolved, patient 3290335 "Demo Patient" (DOB 1913-11-12) created, **sample 2646314 / accession 2610026191 / order 11492640** placed. `emr_sample` id 6670 control_id `NxMsg1`, emr_order_id `26-0012 - A`.
- But the order is EMPTY: `order_input.orderItems = []`, `emr_sample.test_input = ''`, 0 tubes / 0 transactions, `order_major_status=pending_payment_order`, `order_billing_issue_status=billing_issue` (chargeMethod patientPayLater, `emr_payment_fail_reason: no payment method`), `order_unified_status=awaiting_sample`. Only v2 row since 2026-09-25 with empty orderItems (MDHQ 60 / THM 30 / FTP 3 / BioInsights 1 all non-empty).
- OBR-4 codes are valid: `VAREQUISTION36^Anemia` and `VAREQUISTION106^Thyroid (all)` both exist in `package_price_mapping` (ids 4 / 21, isOrderable TRUE); not in the ClearSky remap table.
- **Root cause: OBR-7 = `20261002115705` (14 digits, with seconds).** `ObrParserService.isICD9` regex requires exactly `yyyyMMddHHmm` (12 digits) and throws `Invalid sampleCollectionTime format`; `parser.service.ts` OBR loop catches per-OBR (`OBR parse failed: ...`, Java line 755-757 swallow-and-continue), so BOTH OBRs were dropped, errorCodes stayed empty, and assembly proceeded with zero items. Java `ParseHL7.isICD9` (`LocalDateTime.parse(..., "yyyyMMddHHmm")`) throws on trailing seconds too, so this is inherited legacy behaviour, not a v2 regression. Reproduced locally: regex rejects `20261002115705` / `20261002115742`, accepts `202610021157`.
- Pod zvwwx's processing logs are NOT in Datadog (only host vmss000000 ships; the 23:00 tick on that host logged "Found 1 items ... 0 file(s) enqueued" while zvwwx fetched the file) — the `OBR parse failed` line could not be read back; conclusion rests on code + reproduction.
- Resend caveat: MSH-10 dedup (`findExistingSampleId(controlId)`) — a resend with `NxMsg1` short-circuits to sample 2646314 and places nothing. Nextech must use a NEW message control id (and ideally new placer numbers) on the retry.
- Secondary: customer 28981 has no payment method on file -> patientPayLater / billing_issue. Needs a decision on how ATCA orders are charged before go-live.
- Open: cancel/void empty sample 2646314 / order 11492640 (prod write, gated — Leo decides); decide whether to make `isICD9` lenient (truncate 14 -> 12) in emr-v2 vs ask Nextech for 12-digit OBR-7.

### [2026-10-19 11:40] CORRECTION: OBR-7 is 8 digits (date only), not 14
- Re-read both archived files from prod pod 6f555c7b87-9sx9n. Decoder does `fields = split('|').slice(1)`, so `obr.fields[6]` = OBR-7 = `20261002` / `20261009` (yyyyMMdd). The 14-digit `20261002115705` is OBR-6 (requested date/time) -- the 10-07 entry mis-indexed it. isICD9 regex still rejects -> same swallow -> same empty order, but the "truncate 14 -> 12" fix idea would NOT work; leniency would have to pad date-only (or fall back to OBR-6).
- Second empty order: hl7_file_input 7314 (`NXHL7Exp 26-0018 - 2.hl7`, 10-09 20:30Z, sample 2650711), OBR-4 VAREQUISTION35 + VAREQUISTION36, same OBR-7 date-only. 7295 (`26-0017`, 10-08) is parse_finished=0, no archive path -- not looked at yet.
- Prod-wide `orderItems": []` with parse_finished=1: NEXTECH 2 (7251, 7314), MDHQ 7 (2025-07..08), Breathermae 1 (2025-11) -- the older ones not checked for cause.

## Approaches Considered
- Followed BIOINSIGHTS-onboarding (2026-07) as the precedent for a vendor-hosted SFTP: connectivity probe -> gated ehr_vendors + sftp_folder_mapping INSERT -> wait for practice scope -> ehr_integrations. Differences: password auth (not key), and this time ALSO inserted the `ehr_vendor_sftp_templates` row so the self-service integration create flow (needs a template, else 400) works for Nextech.
- pipeline_location=cloud (not onprem): AKS prod pod egress to interface02.nextechapp.com:22 verified; on-prem egress not verifiable from local (no SSH access to appserver04 in this session). BioInsights cloud folder has been live-scanning since 2026-07-23 with no issue. Rollback = UPDATE pipeline_location='onprem'.

## Decisions Made
### [2026-09-22 10:36]
- Vendor code `NEXTECH`, name `Nextech`, supported_hl7_versions `["2.3"]` (default; Nextech's actual HL7 version unconfirmed), is_public=0 until go-live (flip at go-live like BioInsights).
- Order path `/965721.Vibrant/Export/`, result path `/965721.Vibrant/Import/`, local order folder `/NEXTECH/Prod/Order/`.
- Did NOT pre-create `/965721.Vibrant/Export/archive/` permanently by hand — the fetcher creates it lazily (idempotent mkdir, `hl7-order-fetch.service.ts`). Verified from local that mkdir + rename into archive + remove all succeed on GoAnywhere, so the fetcher's default `HL7_REMOTE_POST_FETCH_ACTION=archive` will work. (An empty `Export/archive/` folder was left by the probe — harmless, identical to what the fetcher creates.)

### [2026-09-24 11:40]
- Did NOT copy the MDHQ peer rows. Mirrored `IntegrationRequestService.create()` (the self-service API path) field-for-field instead, so the row is indistinguishable from an API-created one:
  - `deriveCapabilityFlags('FULL_INTEGRATION')` -> ordering/result/sftp = 1/1/1, api = 0.
  - Non-Cerbo branch: template paths copied verbatim (no `{folder}` substitution) -> `/965721.Vibrant/Export/`, `/965721.Vibrant/Import/`. **This is why Nextech needed no per-practice folder slug and MDHQ would have.**
  - `legacy_emr_service` = `template.emr_name` = NEXTECH.
  - VP-17460: vendor SFTP credentials copied into the row for audit while `use_vendor_sftp_config=1` keeps the read path on the vendor preset (so it rotates with the vendor).
  - VP-16779: `msh06_receiving_facility` defaults to clinicId -> '20834'.
  - LIS-7716 carry-over: clinic 20834 has no other LIVE integration, so `report_option` falls to CLASSIC rather than being inherited.
- **`pipeline_location='cloud'`, taken from `sftp_folder_mapping` id 288, NOT from the MDHQ convention (`onprem`).** Getting this wrong is silent: no pod would scan the folder and orders would simply accumulate.
- Also wrote the `ehr_integration_status_history` row the API writes (NULL->PENDING). Without it the row has no history in the status-management UI and looks unlike every API-created row.
- Deliberately did NOT reproduce `sendEmailNotifications()` — it mails the provider and the internal team, which Leo had not asked for and which would have gone out while the practice question was still open.
- `kit_delivery_option` = BOTH_BLOOD_AND_NON_BLOOD: the only field with no instruction. API code defaults to NO_DELIVERY, but the DB default and both recent real NEW_INTEGRATION rows (Telos 21786, Nancy Vance 24183) use BOTH. Flagged to Leo as changeable.
- Two-step by Leo's choice: created PENDING first (inert — both the ordering filter and `sftp.service.getSftpConfig` require status LIVE), then flipped to LIVE in a second gated transaction once he confirmed clinic 20834.

## Code Changes
- No code. Prod data only (lis_emr @ lisportalprod2), single transaction with pre-check guards + in-tx 100% readback, runner `lis-backend-emr-v2/scripts/_nextech-apply.js` (gitignored, password read from a scratchpad file, never printed):
  - `ehr_vendors` id=47: NEXTECH / Nextech, interface02.nextechapp.com:22, user Vibrant.965721@nextechapp.com, password set, key NULL, ordering=/965721.Vibrant/Export/, result=/965721.Vibrant/Import/, is_active=1, is_public=0, created_by/updated_by=Leo. Applied 2026-09-22 17:36:10Z.
  - `sftp_folder_mapping` id=288: /965721.Vibrant/Export/ -> /NEXTECH/Prod/Order/, emrName=NEXTECH, use_v2_pipeline=1, pipeline_location=cloud (second cloud folder ever; other 200 are onprem).
  - `ehr_vendor_sftp_templates` id=33: vendor 47, emr_name NEXTECH, order/local/result paths as above.
- Rollback: `DELETE FROM ehr_vendor_sftp_templates WHERE id=33; DELETE FROM sftp_folder_mapping WHERE id=288; DELETE FROM ehr_vendors WHERE id=47;` (no FK children yet).

### [2026-09-24 11:43 / 11:46] First provider integration
- No code. Prod data only, two gated transactions, runners in the session scratchpad (`add-nextech-28981.js`, `golive-nextech-28981.js`); credentials read from `ehr_vendors` inside the transaction, never written into the script or any report.
- `ehr_integrations` id **cmufvrntc0000dq0x51sbd986** @ 18:43:51Z: customer_id 28981, clinic_id 20834, ehr_vendor_id 47, FULL_INTEGRATION / NEW_INTEGRATION / NORMAL, customer_npi = effective_npi = 1215931902, contact Jessica Marshall <j.marshall@nextech.com> 937-395-7319 (Senior Technical Implementation Specialist), ordering/result/sftp = 1/1/1, api 0, hl7_version 2.3, msh06 '20834', use_vendor_sftp_config 1, sftp_* copied from vendor 47, ordering path /965721.Vibrant/Export/, result path /965721.Vibrant/Import/, archive NULL, report_option CLASSIC, kit_delivery BOTH_BLOOD_AND_NON_BLOOD, result_push_level WHOLE_ORDER, pipeline_location cloud, legacy_emr_service NEXTECH, requested_by `nextech-integration-28981-20260924`. Status PENDING at insert.
- Status flip PENDING -> LIVE @ 18:46:19Z, `last_modified_by` same tag, `ehr_integration_status_history` now NULL->PENDING | PENDING->LIVE.
- Guards used — create: no existing row for this customer/NPI; vendor 47 active with complete SFTP; template exists with no unsubstituted `{folder}`; `sftp_folder_mapping` exists for the order folder (else nothing ever fetches); clinic has no LIVE integration (so CLASSIC is correct, not a silent downgrade). Go-live: row still PENDING; **no other LIVE row on this NPI** (else the flip would move someone else's routing).
- Rollback: `UPDATE ehr_integrations SET status='PENDING' WHERE id='cmufvrntc0000dq0x51sbd986';` then `DELETE` that row + its 2 status_history rows. Vendor/template/mapping (47/33/288) are shared and must stay.

## Test Results
### [2026-09-22 10:20] Local connectivity (paramiko, scratchpad probes)
- TCP + auth OK (0.7 s), server SSH-2.0-GoAnywhere7.10.2, host key ssh-rsa 9cb2539686b52e69703318abd3959edf.
- chroot root shows only `965721.Vibrant/` with `Export/` and `Import/` (both empty).
- Import: put 37-byte test file -> stat -> get (byte-identical) -> remove: ALL OK, folder left empty.
- Export: mkdir archive OK, put probe file OK, rename into archive OK, remove OK (= exact fetcher post-fetch flow).
- AKS prod pod (lis-emr-v2-deployment-prod-74688f6774-4dzfp) `net.connect` to interface02.nextechapp.com:22: connected, banner received. No allowlist negotiation needed.
- Independent read-only readback (MCP lisportalprod2 read-only account, separate connection) after INSERT: vendor 47 / mapping 288 / template 33 all match plan; no stray NEXTECH/965721 rows elsewhere.

### [2026-09-22 10:45] Pipeline LIVE-verified (consumer-layer readback)
- 17:45:00Z cron tick on AKS prod pod: "Scanning 2 v2-enabled SFTP folder(s) [cloud]" -> "Connecting to SFTP server: interface02.nextechapp.com:22" (attempt 1/3, ~1.7 s) -> "Listing files in directory: /965721.Vibrant/Export/" -> "Found 1 items" (= archive/) -> "HL7 fetch complete: 0 file(s) enqueued from 2/2 folder(s)". Order pipeline now scans Nextech every 15 min with the DB-stored password.
- Safety: zero ehr_integrations rows for vendor 47 -> any file that lands now fails at customer_not_found, no order is placed; results cannot be pushed to Nextech until an integration row with result_enabled exists.

### [2026-09-24 11:43-11:50] First integration row
- Both transactions dry-run (rolled back) before `--commit`. Create: 5 guards pass, **37/37 fields** compared in-tx. Go-live: status changed and every other field byte-identical to the pre-UPDATE snapshot; `UPDATE` asserted to touch exactly 1 row.
- Independent read-only readback (MCP lisportalprod2, different account/connection from the Prisma writer): all fields match, history correct.
- Reverse audit with wider criteria — by NPI (any status), by customer_id, by clinic 20834, by vendor 47 — **each returns exactly 1**. No duplicates, nothing missed.
- Consumer-layer: ran the real `resolveOrderingIntegration` filter+ordering. While PENDING the row ranked first (type_rank 0) but `passes_live_filter=0` = correctly inert. After LIVE it is the sole candidate -> customer 28981. `sftp.service.getSftpConfig` filter (customer + result_enabled + sftp_enabled + LIVE) also matches exactly 1.
- **Third-party channel round-trip** (own side succeeding != channel alive): connected to interface02.nextechapp.com:22 with vendor credentials via `ssh2-sftp-client` (same library the service uses); `/965721.Vibrant/Export/` and `/965721.Vibrant/Import/` both exist and are listable. Export contains only `archive/` (from the 09-22 probe); orders will land in the Export root, not hidden in a subdirectory. List-only, no writes.

## User Feedback

## Next actions
- **Still open: reconcile the practice.** The thread's practice is "Alzheimer's Treatment Centers of America"; the row is bound to clinic 20834 "Naples Center for Functional Medicine" (Leo's call). If Nextech's HL7 carries a different practice identifier, `msh06_receiving_facility` and possibly `clinic_id` have to move. Ask Jessica for the practice identifier Nextech puts in MSH-6 / the sample HL7.
- **No sample HL7 has ever arrived.** First real file is the end-to-end test; watch `hl7_file_input` for sftpDir `/965721.Vibrant/Export/` and confirm it gets a sample_id under customer 28981 (not customer_not_found / emr_code_not_found). Test-code mapping in OBR-4 is entirely unvalidated for this vendor.
- `kit_delivery_option` = BOTH_BLOOD_AND_NON_BLOOD is an un-instructed default; confirm with Leo/the practice.
- Flip `ehr_vendors.is_public=1` at go-live (still 0).
- Further providers at this practice: same recipe, only customer_id / customer_npi / msh06 change.
- Tickets: VP-18336 Done (vendor build-out). QA twin **QH-7179 still To Do** — it is the end-to-end test. No Jira comment posted for today's change (per instance rule: draft only).

## Failures
- `mcp__vibrant__mysql_query` (lisportalprod) has no `lis_emr` DB — prod lis_emr is only on lisportalprod2 (`lisportal_mysql_query`, read-only). Writes go through emr-v2 `.env` DATABASE_URL (lis_emr account) via Prisma runner.

## Retrospective

## Lessons Learned
- Vendor email folder labels ("Export - Orders") are not paths; always `ls` the real tree before writing paths into ehr_vendors.
- **When a human instruction names a vendor/practice that the source document contradicts, the recently-provisioned-but-unused config is the tiebreaker.** MDHQ vs Nextech was settled not by re-reading the email but by noticing vendor 47 had template + folder mapping + zero integrations, created two days earlier — the exact shape of "mid-onboarding".
- **Build a new integration row from the API service code, not from a peer row.** Peer-copying would have produced `pipeline_location='onprem'` (silent dead end — no pod scans the folder), `legacy_emr_service='MDHQ'`, and no `ehr_integration_status_history` row. `IntegrationRequestService.create()` is the spec; peers are only evidence of what defaults people picked.
- The per-practice SFTP folder slug problem is Cerbo/MDHQ-specific (`{folder}` placeholder in the template). Non-Cerbo vendors copy concrete template paths, so "which folder?" is not a question to ask for them — check the template for `{folder}` before asking anyone.
- Correction to a claim made mid-session: `sftp_archive_path` on ehr_integrations is inert (only the configuration-management CRUD reads it), but that does NOT mean the remote `archive/` folder is unused — the fetcher archives via `HL7_REMOTE_POST_FETCH_ACTION` (default `archive`) in `hl7-order-fetch.service.ts`, independent of that column. Two different mechanisms with confusingly similar names.

### [2026-10-20 14:40] Jessica 10-20 14:16Z: result received, PID-2.1 and OBR-2.1 missing
- Her mail (to Britney/support, Leo cc): "We were missing the patient ID in PID 2.1 and the order # in OBR 2.1. Do you need an additional order for testing?" Attachments 2610196534.pdf + Demo_Patient_1_000005.pdf; inline images are only signature icons.
- Order 26-0018 sent: PID-2 `1^^^Nextech Practice` (also PID-3/PID-4 = 1), ORC-2/OBR-2 per test `26-0018 - A` / `26-0018 - B`, ORC-4 `26-0018`.
- emr-v2 result encoder (hl7-encoder.service.ts buildPID/buildOBR): PID-2 hard-coded empty, PID-3 = Vibrant patientId; ORC-2/OBR-2 = emrOrderId which result-generation sets to julienBarcode (accession) for every vendor except THM (THM reads emr_sample.emr_order_id).
- Stored today: emr_sample.emr_order_id = `26-0018 - A` (first OBR only). EMR patient id from PID-2 is NOT stored anywhere (order_input has Vibrant patientId 3290335 only).
- Fix needs code: OBR-2 can follow the THM precedent; PID-2 needs persistence of the inbound PID-2 (schema or reuse). Open: per-OBR placer (A/B) vs single. Waiting on Leo.

### [2026-10-20 15:00] Leo feedback on the PID-2/OBR-2 reply draft
- First draft said "we'll update it to send both back" + "no additional test order is needed yet" -> Leo: wrong, it commits to a change before requirements are confirmed. Correct engineering order for a vendor's "field X is missing": (1) state what our system sends today, (2) hand requirement verification to the PM (@Keith). No promise of a fix, no answer on next test order.
- Old draft deleted; new reply-all draft created on Jessica's 10-20 14:16Z mail (not sent; send from Outlook, convert @Keith to a real mention).

### [2026-10-20 18:40] Reply sent, Keith asked Jessica the requirement questions; rule fixed by Leo
- Leo sent the current-state reply 17:48Z. Keith (PM) replied 18:32Z asking Jessica: per-test (26-0018 - A) vs base (26-0018) matching; which number when one result OBR covers several ordered tests; whether unanswered per-test orders stay open; where to put our accession; which field carries the Nextech patient ID and whether to echo it in result PID-2. Also told her: another test order will be needed, hold until we say ready.
- Leo's rule (2026-10-20): OBR-3 always = accession. OBR-2 default = accession; only vendors that specify otherwise (THM, NEXTECH) get their own placer number. Prod check: THM already OBR|1|12958|2610076237 (placer|accession); FTP/MDHQ/NEXTECH OBR-2 = OBR-3 = accession.
- Implementation when answered: extend THM branch in result-generation buildSampleInfo (~1693) to NEXTECH, but keep file name (~2436) and PDF download (~3027) on accession. PID-2 needs a new emr_sample column (schema change, manual prod ALTER first). Waiting on Jessica's answers.

### [2026-10-23] Jessica answered Keith's questions (relayed via Slack)
- Clear: PID-2 carries Nextech patient id on all orders, echo it in result PID-2. OBR-3 may carry our accession. OBR-2 = their order number.
- Not clear: Q1 (per-test vs base matching) not answered; she counter-proposed one order with multiple tests, no code in OBR-4.1, test name+code in NTE -> our parser places from OBR-4, would produce an empty order. Q3: every order needs a result to complete -> 26-0018 - B stays open unless a result carries B.
- Our side today: encoder emits one ORC/OBR per result panel (hl7-encoder.service.ts ~140), all with the same placer; emr_sample.emr_order_id stores only the first OBR-2 (A). Per-test placer needs ordered-package -> placer mapping + panel -> package mapping.
- Assessment to Leo: PID-2 + OBR-3 can proceed; OBR-2 needs one more question to Nextech (keep OBR-4 codes; per-panel OBR-2 A/B vs all-A closes B?).
- Leo 10-23: Q1 (codes only in NTE) -> state plainly not supported, do not ask permission. Q2 -> demand a definitive answer. Sales negotiates with Nextech, not us.
- 10-23: Leo sent the reply; Sales to get Nextech's answer on Q2. PID-2/OBR-3 not started yet.

### [2026-10-26] Jessica 10-26 13:31Z: both OBR-2 questions answered, nothing missing from Nextech
- Q1: confirmed codes-only-in-NTE is not supported; each test = own OBR with code in OBR-4.1.
- Q2: each result OBR must carry the matching per-test order number in OBR-2 (26-0018 - A / - B / - C). "Let me know when you are ready for an additional order."
- Ball is on our side: PID-2 echo (new emr_sample column, manual prod ALTER first), OBR-3 = accession, OBR-2 per-test placer (needs ordered OBR-4 code -> placer persistence + result panel -> ordered test mapping). No Jira ticket exists for this work yet (checked 10-26).
- 10-26: Leo asked for one ticket covering all three -> created VP-19028 (Task, Dev To Do, assignee Leo, labels emr-integration/nextech). Finding while writing it: OBR-3 already = accessionId in buildOBR, so item 2 is verify-only. Not started.

### [2026-10-26] VP-19028 implemented locally (not pushed)
- Worktree ~/src/lis-backend-emr-v2.worktrees/VP-19028, branch feature/leo/VP-19028 from origin/staging 8fe2ada, commit 839ad7e.
- Design: new nullable emr_sample.emr_patient_id VARCHAR(255) + emr_placer_orders TEXT (JSON OBR-4.1 upper -> OBR-2.1, fallback preceding ORC-2), written for all vendors, read only when emr_service = NEXTECH. emr_order_id untouched (file name/PDF download stay on accession). Encoder: PID-2 = patient.emrPatientId; ORC-2/OBR-2 = panel.placerOrderNumber || order.emrOrderId. Unmapped panel -> first placer (emr_order_id), logged.
- L4 evidence the mapping holds: 10-19 result for 2610196534 (result_transmission_records) has OBR-4 VAREQUISTION36 / VAREQUISTION35 = exactly the ordered OBR-4.1 codes.
- Tests: full jest 182 suites green (fresh worktree needs `npm run prisma:generate:test` first or 5 suites fail on missing .prisma/test-client). nest build clean, migration lint 0 findings.
- Mistake caught: symlinked worktree node_modules to the main checkout and `prisma generate` overwrote the main checkout's client; restored by re-running generate in the main checkout. Use npm ci per worktree.
- Waiting on Leo: approve manual ALTER on staging (192.168.60.11) + prod (lisportalprod2), then push + PR to staging.

### [2026-10-26] VP-19028 DDL applied, PR #509 open, Jessica reply drafted
- ALTER emr_sample ADD emr_patient_id VARCHAR(255) NULL, emr_placer_orders TEXT NULL (INSTANT, lock_wait_timeout=5): staging 192.168.60.11 (8.0.44, 46 ms, 965 rows all NULL), prod lisportalprod2 (8.4.9-azure — not 8.0.45 as the gate skill says; 79 ms, 2406 rows all NULL). Prod read back on the read-only MCP account. Script: mysql2 via worktree node_modules (no mysql CLI on this Mac).
- PR https://github.com/Vibrant-America/lis-backend-emr-v2/pull/509 -> staging, head 839ad7e. Not merged yet (Leo asked only to open it).
- Outlook reply-all draft on Jessica 10-26 13:31Z, id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABj485egAA (inline images: send from Outlook). Content: confirm PID-2 / per-test OBR-2 / accession OBR-3, we'll say when ready for the next test order. No questions asked.

### [2026-10-26 20:51Z] VP-19028 merged to staging (b4a975f) and live-verified PASS
- Pod lis-emr-v2-deployment-staging-f7cc6d94f-g6thk (image b4a975f, up 20:48:07Z), DB 192.168.60.11. Script in scratchpad verify-vp19028.js ran the DEPLOYED parser helpers / finalizer.writeEmrSample / generateHl7Content + real encoder against the real staging DB; stubbed only panel grouping, approved time, PDF (add_report=0).
- Intake: placers {VAREQUISTION35: 26-0018 - A, VAREQUISTION36: 26-0018 - B}, PID-2 '1', written and read back from emr_sample.
- NEXTECH ORU: PID|1|1|..., OBR|1|26-0018 - B|2610196534|VAREQUISTION36, OBR|2|26-0018 - A|2610196534|VAREQUISTION35, unmapped VATEST99 -> 26-0018 - A + WARN. MDHQ control unchanged (PID-2 empty, OBR-2 = accession).
- Cleanup: fake row sample_id 990190280 / control_id VP19028-STG deleted, reverse count 0. Pod logs 10 min: 0 ERROR / Unknown column. /tmp/verify-vp19028.js left in the pod (rm blocked by safety check; gone on next restart).
- Staging DB has no NEXTECH ehr_vendors row (encoder test-name mapping lookup warns); prod has vendor 47.
- Next: release PR staging -> main (Leo merges), then send Jessica the draft and request the additional test order.
- 10-26: release PR #510 staging -> main opened (head = staging b4a975f, only VP-19028). Waiting on Leo merge; then confirm prod pod image, send Jessica draft.

### [2026-10-27] Dream: release #510 already merged to main
- GitHub: lis-backend-emr-v2 #510 MERGED 2026-10-26 23:47:56Z (merge commit 6edbf862). The last section above still says "waiting on Leo merge".
- Not yet recorded: prod pod image = 6edbf862 (Jenkins deploy, AKS + on-prem), post-deploy pod log check, sending the Jessica draft, asking Nextech for the next test order.

### [2026-10-27] Prod deploy verified; waiting to ask Nextech for the next test order
- AKS prod `lis-emr-v2-deployment-prod-5dc68667b9-5m2sr` image 6edbf862 (= main, #510), up 21h, 0 restarts. 21h logs: 0 Unknown column / emr_patient_id / emr_placer_orders errors; 7 ERROR lines are unrelated (RANGE_ERROR mapper, kafkajs OffsetCommit/Fetch). On-prem prod not checked (no kube context on this Mac); Nextech integration runs on AKS.
- VP-19028 still Dev To Do, QH-7988 To Do. Acceptance needs Nextech's next multi-test order closing every ordered test.
- Outlook MCP needs re-auth; could not confirm whether the 10-26 reply to Jessica was sent.
- 10-26 21:56Z Leo's "Thanks for confirming, we'll let you know when ready" reply was sent. 10-27: reply-all draft on it created (not sent), id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABj4_YCQAA, To Jessica/Britney/support, Cc Mingxi/Jason/Xiaoye/Javier/Keith/Carisa/Jordan/Rachel. Body: ready for the additional test order, include at least two tests. Quoted inline images -> send from Outlook.
- 10-27: Leo sent the test-order request. Next: watch hl7_file_input for a new Nextech file (sftpDir /965721.Vibrant/Export/, AKS prod) -> verify emr_sample.emr_patient_id + emr_placer_orders populated -> after result, confirm ORU PID-2 / per-test OBR-2 in result_transmission_records -> Jessica confirms all tests closed -> VP-19028 Dev Complete, QH-7988 + VP-19028 Done.

### [2026-10-28] Order 26-0019 received and verified on prod
- Jessica 10-28 14:28Z sent order 26-0019 (attachment Order 10-28.txt) and said MSH carries the practice ID: MSH-4 = 20834 = our clinic_id 20834 (practice reconcile item resolved for this practice).
- hl7_file_input 7442 `NXHL7Exp 26-0019 - 2.hl7` received 14:30:08Z, placed 14:30:12Z on AKS prod pod 5dc68667b9-5m2sr (6edbf86): sample 2660850, accession 2610286139, no errors.
- emr_sample 6848: emr_patient_id `5` (= PID-2.1), emr_placer_orders {VAREQUISTION103: 26-0019 - A, VAREQUISTION36: 26-0019 - B} (= OBR-4.1 -> OBR-2 in the file), emr_order_id `26-0019 - A`, test_input `9,4` (single, multi-ORC fix holds), order total 154.47 (items 20 + 9.47 + 125 lab fee).
- Reply-all draft to Jessica created (not sent), id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABj4-FWQAA.
- Next: demo result for 2660850 (previously generated by support/Zhenhe) -> check result_transmission_records ORU: PID-2 = 5, OBR-2 per panel A (Lipids) / B (Anemia), OBR-3 = 2610286139 -> Jessica confirms both close.
