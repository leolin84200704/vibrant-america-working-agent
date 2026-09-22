---
id: NEXTECH-onboarding
type: stm
category: emr_integration
status: active
score: 0.00
base_weight: 1.0
created: 2026-09-22
updated: 2026-09-22
links: []
relations:
  unblocked_by: []
  blocks: []
  sibling:
  - BIOINSIGHTS-onboarding
unblock_when: "Nextech / ATCA provide practice scope (provider IDs, NPIs, clinic) + sample HL7 order; test = a .hl7 lands in /965721.Vibrant/Export/ and shows up in hl7_file_input"
tags: [vp-18336, nextech, atca, sftp, vendor-onboarding, alzheimers-treatment-centers]
summary: "New EMR vendor Nextech (bi-directional, for Alzheimer's Treatment Centers of America) — vendor-hosted password SFTP (GoAnywhere) interface02.nextechapp.com:22. 2026-09-22 connectivity fully verified from local (auth, ls, put/get/remove in Import, mkdir+rename archive flow in Export) and AKS prod pod egress OK. Prod INSERTed: ehr_vendors id=47 NEXTECH (is_public=0), sftp_folder_mapping id=288 /965721.Vibrant/Export/ -> /NEXTECH/Prod/Order/ pipeline_location=cloud, ehr_vendor_sftp_templates id=33. No ehr_integrations yet — waiting on practice scope + sample HL7 from Nextech (Jessica Marshall). Tracking ticket VP-18336."
---
# NEXTECH-onboarding - Work Loop Record

## Ticket Analysis
### [2026-09-22 10:30]
- Source: email thread "Alzheimer's Treatment Centers of America | Vibrant Wellness Nextech Bi-Directional Integration Purchase". Nextech contact: Jessica Marshall (Senior Technical Implementation Specialist, j.marshall@nextech.com, 937-395-7319); CC Carisa Trimmer, Jordan Skeens, Rachel Tomaiolo (Nextech); Xiaoye Li, Britney Little, Jason Thai, Javier Alvarez, Keith (Vibrant side).
- Connectivity = SFTP hosted by Nextech (GoAnywhere 7.10.2): host `interface02.nextechapp.com`, port 22, user `Vibrant.965721@nextechapp.com`, password auth (32 chars, stored ONLY in prod `ehr_vendors.sftp_password`; not in any repo/STM).
- Email labels "Export - Orders" / "Import - Results" are labels, NOT folder names. Real paths: `/965721.Vibrant/Export/` (Nextech exports orders here; we pick up) and `/965721.Vibrant/Import/` (we drop results here; Nextech imports). Both empty on 2026-09-22.
- Leo instruction: 把連接建立好 (set up the connection).
- Jira: zero hits for "Nextech" / "Alzheimer" before 2026-09-22. Ticket created 2026-09-22 on Leo's request: **VP-18336** (Task, P2, assignee Leo, Dev To Do) https://vibrantamerica.atlassian.net/browse/VP-18336 . Created via Atlassian MCP; the vibrant MCP `create_jira_issue` returned 403 (no create permission on VP).

## Approaches Considered
- Followed BIOINSIGHTS-onboarding (2026-07) as the precedent for a vendor-hosted SFTP: connectivity probe -> gated ehr_vendors + sftp_folder_mapping INSERT -> wait for practice scope -> ehr_integrations. Differences: password auth (not key), and this time ALSO inserted the `ehr_vendor_sftp_templates` row so the self-service integration create flow (needs a template, else 400) works for Nextech.
- pipeline_location=cloud (not onprem): AKS prod pod egress to interface02.nextechapp.com:22 verified; on-prem egress not verifiable from local (no SSH access to appserver04 in this session). BioInsights cloud folder has been live-scanning since 2026-07-23 with no issue. Rollback = UPDATE pipeline_location='onprem'.

## Decisions Made
### [2026-09-22 10:36]
- Vendor code `NEXTECH`, name `Nextech`, supported_hl7_versions `["2.3"]` (default; Nextech's actual HL7 version unconfirmed), is_public=0 until go-live (flip at go-live like BioInsights).
- Order path `/965721.Vibrant/Export/`, result path `/965721.Vibrant/Import/`, local order folder `/NEXTECH/Prod/Order/`.
- Did NOT pre-create `/965721.Vibrant/Export/archive/` permanently by hand — the fetcher creates it lazily (idempotent mkdir, `hl7-order-fetch.service.ts`). Verified from local that mkdir + rename into archive + remove all succeed on GoAnywhere, so the fetcher's default `HL7_REMOTE_POST_FETCH_ACTION=archive` will work. (An empty `Export/archive/` folder was left by the probe — harmless, identical to what the fetcher creates.)

## Code Changes
- No code. Prod data only (lis_emr @ lisportalprod2), single transaction with pre-check guards + in-tx 100% readback, runner `lis-backend-emr-v2/scripts/_nextech-apply.js` (gitignored, password read from a scratchpad file, never printed):
  - `ehr_vendors` id=47: NEXTECH / Nextech, interface02.nextechapp.com:22, user Vibrant.965721@nextechapp.com, password set, key NULL, ordering=/965721.Vibrant/Export/, result=/965721.Vibrant/Import/, is_active=1, is_public=0, created_by/updated_by=Leo. Applied 2026-09-22 17:36:10Z.
  - `sftp_folder_mapping` id=288: /965721.Vibrant/Export/ -> /NEXTECH/Prod/Order/, emrName=NEXTECH, use_v2_pipeline=1, pipeline_location=cloud (second cloud folder ever; other 200 are onprem).
  - `ehr_vendor_sftp_templates` id=33: vendor 47, emr_name NEXTECH, order/local/result paths as above.
- Rollback: `DELETE FROM ehr_vendor_sftp_templates WHERE id=33; DELETE FROM sftp_folder_mapping WHERE id=288; DELETE FROM ehr_vendors WHERE id=47;` (no FK children yet).

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

## User Feedback

## Next actions
- Leo: send `drafts/NEXTECH-onboarding-reply-to-jessica-draft.md` (connectivity confirmed + ask practice scope / sample HL7 / HL7 version / result spec / MSH-6 identifier).
- On vendor reply: review sample HL7 in hl7_file_input + /NEXTECH/Prod/Order/ (cloud pod local), assess transformer mapping, then gated ehr_integrations INSERT per provider (use_vendor_sftp_config=1, sftp_result_path=/965721.Vibrant/Import/, pipeline_location=cloud), flip is_public=1 at go-live.
- Tracking ticket: VP-18336.

## Failures
- `mcp__vibrant__mysql_query` (lisportalprod) has no `lis_emr` DB — prod lis_emr is only on lisportalprod2 (`lisportal_mysql_query`, read-only). Writes go through emr-v2 `.env` DATABASE_URL (lis_emr account) via Prisma runner.

## Retrospective

## Lessons Learned
- Vendor email folder labels ("Export - Orders") are not paths; always `ls` the real tree before writing paths into ehr_vendors.
