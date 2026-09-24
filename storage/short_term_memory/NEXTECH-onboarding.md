---
id: NEXTECH-onboarding
type: stm
category: emr_integration
status: active
score: 0.00
base_weight: 1.0
created: 2026-09-22
updated: 2026-09-24
links: []
relations:
  unblocked_by: []
  blocks: []
  sibling:
  - BIOINSIGHTS-onboarding
unblock_when: "End-to-end test order from Nextech; test = a .hl7 lands in /965721.Vibrant/Export/, gets a sample_id in hl7_file_input under customer 28981, and the result PDF+HL7 land in /965721.Vibrant/Import/. First provider is LIVE since 2026-09-24, so a file arriving now WILL place an order."
tags: [vp-18336, qh-7179, nextech, atca, sftp, vendor-onboarding, alzheimers-treatment-centers, ehr-integrations, george-moricz, customer-28981]
summary: "New EMR vendor Nextech (bi-directional, for Alzheimer's Treatment Centers of America) — vendor-hosted password SFTP (GoAnywhere) interface02.nextechapp.com:22. 2026-09-22 connectivity fully verified from local (auth, ls, put/get/remove in Import, mkdir+rename archive flow in Export) and AKS prod pod egress OK. Prod INSERTed: ehr_vendors id=47 NEXTECH (is_public=0), sftp_folder_mapping id=288 /965721.Vibrant/Export/ -> /NEXTECH/Prod/Order/ pipeline_location=cloud, ehr_vendor_sftp_templates id=33. FIRST ehr_integrations row added 2026-09-24 (id cmufvrntc0000dq0x51sbd986, customer 28981 George Moricz MD NPI 1215931902, clinic 20834, FULL_INTEGRATION, LIVE) — order routing for that NPI now resolves to 28981 and results push to /965721.Vibrant/Import/. Still no sample HL7 seen from Nextech. VP-18336 Done 2026-09-22 (vendor build-out); QA twin QH-7179 still To Do."
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
