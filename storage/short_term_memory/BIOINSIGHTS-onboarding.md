---
id: BIOINSIGHTS-onboarding
type: stm
category: emr_integration
status: active
relations:
  unblocked_by: []
  sibling:
  - BIOINSIGHTS-SFTP-KEY
unblock_when: 'BioInsights grants account perms (test: sftp key-auth to sftp.bioinsights.com:2022
  then ls / — currently auth OK but ls/stat/put all fail); waiting on Thomas reply
  to 2026-07-21 email'
created: 2026-07-21
updated: 2026-10-15
links:
- BIOINSIGHTS-SFTP-KEY
- HL7FAIL-20261019-PARSLEY-KHATRI
- INCIDENT-20261013-bioinsights-jag-crossmap
- NEXTECH-onboarding
- VP-17827
- VP-18138
- VP-18194
- VP-18372
- VP-19006
- emr-integration
- fhir-api
tags:
- bioinsights
- sftp
- key-auth
- vendor-onboarding
summary: 'New EMR vendor BioInsights — first key-based (non-password) SFTP integration.
  Code shipped: emr-v2 PR no VP ticket yet): migration 20260720_add_sftp_private_key
  adds nullable sftp_private_key to ehr_vendors + ehr_integrations and private_key
  to emr_sftp_source; order fetch accepts key-only credential rows (VP-17385 drift
  check extended to privateKey); result push passes key through to connect. Migration
  must be applied MANUALLY to prod (lisportalprod2) and staging (192.168.60.11) BEFORE
  deploying the code (prod not Prisma-managed). Connection per vendor (Thomas): sftp.bioinsights.com:2022,
  user vibrant-wellness, ed25519 keypair (PPK v3 unencrypted at ~/Downloads/bioinsights_key.ppk;
  emr-v2 needs OpenSSH PEM — convert with puttygen). 2026-07-21 verified from local:
  auth OK, but account has ZERO perms (ls/stat/put all fail) — vendor-side provisioning
  incomplete. Migration verified applied prod+staging; PR 33 existing password vendors
  unaffected; AKS pod egress to bioinsights:2022 OK. 2026-07-21 email sent to Thomas
  (perms + dir layout + sample HL7). STATUS: waiting on vendor reply.'
jira_status: none
score: 0.1403
---

# BioInsights EMR vendor onboarding (SFTP, key-based auth)

## Facts

### [2026-07-21 12:00]
- Vendor connection (from Thomas @ BioInsights, tested OK by company IT):
  - Host `sftp.bioinsights.com`, port `2022`, username `vibrant-wellness`
  - Auth = ed25519 keypair, comment `vibrant-wellness-bioinsights-sftp`
  - Private key: `~/Downloads/bioinsights_key.ppk` (PPK v3, UNENCRYPTED — should move out of Downloads into credential store)
  - Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF1/iaD2dcHdpj/WgGDC6MvRmMdqGa0oMjfixyQ/O45t`
- emr-v2 SFTP client wants `privateKey` as **OpenSSH PEM string** (`sftp-connection.service.ts`), NOT ppk. Convert: `puttygen x.ppk -O private-openssh -o x.pem` (brew install putty).
- Local connection test 2026-07-21: auth SUCCEEDS; `ls /` returns "Couldn't read directory: Failure" (chroot/perm); probed orders/results/inbound/outbound/in/out/upload/download/files/vibrant*/home — none exist. **Remote dir layout unknown.**

## Code state (done)
- `lis-backend-emr-v2` PR #275 MERGED to main 2026-07-20 (also in staging). Branch `feature/leo/bioinsights-sftp-key`. Commits:
  - `b6dc99d` migration `20260720_add_sftp_private_key`: ALTER ehr_vendors ADD sftp_private_key TEXT NULL; ehr_integrations ADD sftp_private_key; emr_sftp_source ADD private_key
  - `365e30b` order fetch: loadCredentialStores accepts password-OR-key rows; key carried through HostGroup into connect(); drift compare includes privateKey (names only, never values)
  - `517e396` result push: key pass-through in sftp.service
- No VP ticket exists for this onboarding (Jira text search 0 hits as of 2026-07-21).

### [2026-07-21 22:30] Verification pass (migration/deploy/regression)
- **Vendor account has ZERO permissions**: auth OK but ls/stat/cd/put ALL fail at root and every probed path (20+ naming conventions + write probe). Server-side provisioning incomplete — BLOCKED ON VENDOR (Thomas). IT's "tested OK" was auth-handshake only.
- **Migration applied on BOTH DBs**: prod (via AKS pod prisma, lis_emr) and staging (staging pod, root@lis_emr) both have ehr_vendors.sftp_private_key + ehr_integrations.sftp_private_key.
- **emr_sftp_source table does NOT exist in either prod or staging DB** — migration's 3rd ALTER inapplicable. Harmless: VP-17460 (merged after PR #275) removed the emr_sftp_source fallback from the fetch path; main reads ehr_vendors only via loadVendorCredentials. NOTE pre-existing landmine: auto-integrate integration-request.service.ts still queries prisma.emrSftpSource (would 1146 at runtime) — unrelated to BioInsights, not touched.
- **Deploy confirmed**: prod image 60fc05cd (= origin/main HEAD, merge PR #280) and staging image 17c5b70 BOTH contain PR #275 (verified via git merge-base --is-ancestor).
- **No regression risk to existing integrations**: prod ehr_vendors 33 rows with sftp_host — all 33 password, 0 key, 0 neither → password-OR-key change alters no existing row's behavior. 12h prod logs: order-fetch 0 errors (ticks normal), sftp 0 errors.
- **Egress OK**: prod AKS pod TCP-connects to sftp.bioinsights.com:2022 directly — no allowlist negotiation needed (unlike VP-17312 batch-5 vendors).

### [2026-07-21 23:00] Email sent to Thomas — WAITING ON VENDOR
- Leo sent the drafted email to Thomas @ BioInsights asking for: (1) account read/write permission provisioning (auth works, zero perms), (2) directory layout (orders pickup dir / results drop dir / archive convention), (3) sample HL7 order files for parsing + transformer-mapping assessment.
- Our side fully ready: PR #275 deployed prod+staging, migration applied, egress from AKS pod to sftp.bioinsights.com:2022 verified.
- NEXT ACTION when Thomas replies: re-run connectivity test (ls + put probe), inspect dir layout, review sample HL7 → decide transformer mapping + integration scope (order/result/bidirectional, which practices) → then gated ehr_vendors INSERT.

### [2026-07-23 10:50] Vendor perms fixed — E2E connectivity PASS + vendor/mapping rows INSERTED (prod)
- Serdar SANRI (Head of Eng, serdar@bioinsights.com — new contact, was Thomas) fixed server perms, created `incoming/` + `outgoing/` at root.
- Local E2E test ALL PASS: ls root/incoming/outgoing OK; put+get roundtrip diff-verified in BOTH folders. Test files `vibrant_test.txt` left on server as evidence (harmless: fetch filter only picks `.hl7,.HL7`).
- Key recovered: ppk still at `~/Downloads/bioinsights_key.ppk` (macOS TCC blocks *listing* Downloads — direct full-path access works; earlier "file gone" was a sandbox illusion). Converted to OpenSSH PEM via puttygen; pubkey matches recorded fingerprint.
- **Prod INSERTs applied 2026-07-23 ~10:47 PT** (single transaction, pre-check guards, in-tx 100% verify; runner `scripts/_tmp-bio-apply.js` pattern):
  - `ehr_vendors` id=46: code=BIOINSIGHTS, sftp.bioinsights.com:2022, user vibrant-wellness, sftp_password=NULL, sftp_private_key=PEM(444 chars), ordering_path=/outgoing/, result_path=/incoming/, **is_public=0** (flip at go-live), created_by/updated_by=Leo
  - `sftp_folder_mapping` id=281: /outgoing/ -> /BIOINSIGHTS/Prod/Order/, emrName=BIOINSIGHTS, use_v2_pipeline=1, **pipeline_location=cloud** (FIRST cloud order folder ever — all other 197 rows are onprem; chosen because AKS egress verified, on-prem egress NOT verified; doubles as VP-17312 order-side canary)
- **ASSUMPTION pending vendor confirm**: direction convention = we PICK UP orders from `/outgoing/`, DROP results into `/incoming/` (from BioInsights server's perspective). Asked Serdar in reply draft. If reversed: 1-column UPDATEs (mapping.server_folder + vendor paths swap).
- Safety: even if files arrive now, no ehr_integrations rows exist -> parse fails at customer_not_found, no orders placed.

### [2026-07-23 11:10] Pipeline LIVE-verified + archive dir created + reply email SENT — WAITING ON VENDOR
- 11:00 PT cron tick (AKS cloud pod): "Scanning 1 v2-enabled SFTP folder(s) [cloud]" -> connected sftp.bioinsights.com:2022 with the DB-stored key (1/3 attempt, 1621ms) -> "fetch complete: 0 file(s) from 1/1 folder(s)". Order pipeline is live-scanning BioInsights every 15 min.
- Created `/outgoing/archive/` on vendor server + verified rename into it (= fetcher's exact post-fetch move). Default HL7_REMOTE_POST_FETCH_ACTION=archive flow works with zero config. Test file now at `/outgoing/archive/vibrant_test.txt` (+ one in `/incoming/`).
- Leo SENT the reply email to Serdar 2026-07-23: connectivity confirmed, archive explained, asked to confirm direction convention (orders=outgoing/, results=incoming/) and to have clinical team prep sample HL7.
- STATUS: waiting on Serdar — (a) direction confirm, (b) sample HL7 files. When samples land in /outgoing/ the pipeline auto-ingests; they will fail safely at customer_not_found (no ehr_integrations yet) and be visible in hl7_file_input for parse/mapping review.
- NEXT ACTION on vendor reply: review ingested sample rows in hl7_file_input + raw files in /BIOINSIGHTS/Prod/Order/; if direction reversed, UPDATE mapping.server_folder + swap vendor ordering/result paths + mkdir archive under the other folder; then define practice scope -> ehr_integrations INSERTs (gated) -> flip is_public=1 at go-live.

### [2026-07-27] Practice scope arrived + ehr_integrations INSERTED — first BioInsights practice live
- **[CORRECTED 2026-10-13]** The JAG details did NOT come from Serdar or any BioInsights thread. They came from **Britney Little (Vibrant Wellness CAM)** on 2026-07-27 13:16 UTC in a separate Zendesk thread "[Vibrant Wellness] Re: Integration" (00WRYM-60YK0) about **Canvas Medical** wanting an HTTP(S) integration, with Payton Smith @ canvasmedical.com CC'd. Original (wrong) note: Office = JAG Holdings Group, LLC, Provider 30248, Practice 132493, "BioInsights appears to ride on Canvas Medical's EMR platform" -- that assumption was never verified and is false. The BioInsights thread (Kristine Legaspi -> BioInsights, May 2026 onward) never names JAG, Canvas or Payton. The ehr_integrations row below attached a Canvas-request practice to the BioInsights vendor.
- 30248 = JAGHP (VP-16987 quarterly CSV client). Identity verified via existing prod row: (30248,132493) already had POWER2PRACTICE RESULT_ONLY LIVE (vendor 4, NPI 1730269200, msh06=30248, /public/, onprem).
- **INSERTED `ehr_integrations` id=cms3icsz700010xlgywfuj8do** (prisma create in guarded tx, dry-run first, in-tx verify + reverse-audit clean): vendor 46 BIOINSIGHTS, FULL_INTEGRATION, LIVE, o1/r1/s1, use_vendor_sftp_config=1 (host+key from vendor row), msh06=**132493** (Practice ID convention), sftp_result_path=/incoming/, ordering via folder mapping /outgoing/ (id=281), report_option=CLASSIC (followed sibling), kit_delivery_option=NO_DELIVERY + kits_options=2 (no-oc fallback — vendor kit behavior UNCONFIRMED), pipeline_location=**cloud**, NPI borrowed from sibling, requested_by=BIOINSIGHTS-onboarding.
- **DOUBLE RESULT DELIVERY flag**: both rows LIVE+result_enabled=1 -> results for 30248 now push to BOTH P2P /public/ AND BioInsights /incoming/. Leo to decide: retire P2P row (REJECTED per removal playbook) or keep during transition.
- Cyberduck access for Leo: key converted to ~/.ssh/bioinsights_vibrant-wellness.pem (2026-07-27); ppk still unencrypted in ~/Downloads (secure-store follow-up stands).
- Still waiting on vendor: sample HL7 files + direction-convention confirm (orders=/outgoing/ assumption unchanged). ORC-12 must carry 30248 for orders to resolve.
- [2026-07-27] Leo SENT reply to Serdar+Payton: technically ready end-to-end; "internal coordination step" (= P2P transition confirm, old platform not named externally); will update immediately; invited sample HL7 into outgoing/. PENDING DECISIONS: (a) P2P row retirement — double delivery to /public/ + /incoming/ is ACTIVE until decided (30248's next report_finished pushes both); manual repush w/o integration_id now targets BioInsights (FULL sorts first in validateEmrIntegration findFirst desc); (b) kits_options=2 unconfirmed; (c) JAG payment method for EMR ordering unverified.

### [2026-09-14] New vendor-side party: devcom (Olena Momotko, BA) building the integration for BioInsights; email thread "Integration with Vibrant Wellness"
- Thread CC: lisa/travis/tracie/paola @bioinsights.com, Tianhao Wang (Vibrant), liana.vinichuk @devcom. Olena 09-09: "thank you for providing access, everything works well" (which access Leo granted is not in memory), asked 4 questions (legal docs, bidirectional/EMR-vs-provider, test catalog w/ CPT+LOINC, remaining steps); 09-14 follow-up, says they are blocked.
- Prod ground truth 09-14: ehr_vendors 46 BIOINSIGHTS is_public=0 unchanged since 07-23; exactly 1 ehr_integrations row (JAG 30248/132493 FULL LIVE); hl7_file_input has ZERO rows for BIOINSIGHTS -> no sample/test order has ever been dropped in /outgoing/. Direction convention (orders=/outgoing/, results=/incoming/) still unconfirmed by vendor.
- Leo draft answers: no legal docs; bidirectional yes but "provider level"; catalog from Zhenhe Zhang. Agent drafted the operational-steps answer + suggested rewording of the provider-level answer (per-provider NPI onboarding, not single-provider limitation).

### [2026-09-18 09:30] devcom sample order ARRIVED (after Leo 09-17 email) — picked up, parse FAILED on placeholder NPI, quarantined
- Olena (devcom) replied 09-17/18: "fixed and sent it to the correct bucket". Verified L4: `/outgoing/vibrant-test-order.hl7` (874 B) fetched by the cloud pod 2026-09-17 14:30 UTC (07:30 PT), moved to `/outgoing/archive/` (archive flow works live), local copy `/EMR_storage/HL7Message_prod/BIOINSIGHTS/Prod/Order/vibrant-test-order.hl7`, `hl7_file_input` id=7126 emr_service=BIOINSIGHTS. First BioInsights order file ever ingested.
- Parse: 5 attempts 14:30-15:15 UTC all `customer_not_found=Balandan`; [RETRY-EXHAUSTED] retry_num=0, parse_finished=0, quarantine id=13 class=customer_not_found reason=UNKNOWN_ORIGIN. Will NOT auto-recover — even after the vendor fixes the file, a resend under a NEW file name is required (dedup by file name).
- Root cause in the file: ORC-12 = `1234567^^Balandan^Paola^^^^^N` -> NPI 1234567 (placeholder). Only registered NPI on the integration is 1730269200 (JAG, ehr_integrations cms3icsz700010xlgywfuj8do). Also OBR-16 same placeholder; MSH-4 sending facility 1234567.
- Other content gaps vs Leo's 09-17 checklist: OBR-4 = `3202^% Omega-6s^L`, `3200^...^L` x3 (3200 reused for 3 different tests) -> vendor-local placeholder codes, NOT our internal test codes; would fail emr_code_not_found next. Test catalog from Zhenhe still pending. IN1-2.1 = C (clinic card) — consistent with one of the two options, JAG preference still unconfirmed. MSH-12 = 2.5 (integration row hl7_version 2.3; not a blocker). Patient = John Doe test record.
- Datadog noise: "Test code exceeds 50 characters ... test_id=7126, ehr_vendor_id=1" logs are UNRELATED (test_id, not hl7_file_input id).
- SIDE FINDING: `/incoming/` holds ~150 result `.hl7` files for customer 30248 dated 2026-07-29 .. 2026-09-18 (from the double-delivery P2P+BioInsights setup) that the vendor has NEVER picked up. Vendor result consumption not happening; raise with vendor / decide on P2P retirement.
- NEXT: Leo replies to Olena (draft given 09-18): file received, ORC-12 must be 1730269200, new file name on resend, test codes pending catalog. When a fixed file lands, expect emr_code_not_found until catalog mapping is done.

### [2026-09-23 11:00] devcom SECOND test file arrived (V00000416.hl7) — NPI fixed, now fails emr_code_not_found on retired codes (daily triage 2026-09-23)
- hl7_file_input 7154, received 2026-09-22 13:15 UTC, cloud pod 74688f6774-4dzfp. ORC-12/OBR-16 = 1730269200 (fixed), MSH-4 = 132493. Customer resolved to JAG (integration cms3icsz700010xlgywfuj8do) — the NPI fix worked. Still John Doe test patient, IN1-2.1 = C.
- OBR-4: `VAREQUISTION279^Gut Zoomer 3.0^L` + `VATEST2270^Vitamin D^L`. Both EXIST in getLegacyPackagePriceMapping but isOrderable=false / priceVa=-1, and the names do not match: VAREQUISTION279 = Gut Zoomer 4.0 (orderTypeId 454), VATEST2270 = Copper Serum. devcom is working from a stale/wrong catalog. Correct orderable codes: VAREQUISTION463 (Gut Zoomer 5.0, priceVw 550) and VATEST70 (Vitamin D, 25-OH, priceVa 20).
- quarantined_orders id 14, failure_class test_code_not_found, OPEN, expires 2026-09-29 14:00 UTC. last_error lacks the VP-17752 "(not orderable in the catalog: ...)" suffix even though PR #375 has been on main since 08-18 — parse ran on the image before f52c6dd (PR #430 rolled 09-23 01:53 UTC); not chased further.
- NEXT: tell Olena the NPI is right, swap the two codes (463 / 70), resend under a NEW file name; confirm which catalog devcom received vs Zhenhe's. Do NOT flip isOrderable on 279/2270 to make the test pass. Report: DailyJob/hl7_fail/triage_2026-09-23.md.

### [2026-09-23 10:05 PT] Full field-level audit of V00000416.hl7 (Leo asked: what else is wrong besides the codes)
Read against `lis-backend-emr-v2` origin/main f52c6dd (`parser.service.ts`, `obr-parser.service.ts`,
`patient-detail-parser.service.ts`, `diagnosis-parser.service.ts`). Findings beyond the two test codes:

**Would corrupt or lose data (vendor must fix)**
- **Email sits in PID-19 -> written to the patient's SSN.** `patient-detail-parser.service.ts` L142 reads
  **PID-20.1** as email (the Vibrant convention, DriversLicense field); L151 reads **PID-19** as SSN. The file
  has `john_doe@grr.la` in PID-19, so `patientSSN` -> `patient-grpc-logic.service.ts` L170 `patientSsn` ->
  createPatientV2 `patient_ssn`, and `patient_email_id` comes out empty. Affects every order once real
  patients start flowing, not just this test.
- **ORC-12 / OBR-16 XCN carries one extra empty component.** `1730269200^^Balandan^Paola^^^^^N` -> XCN.2
  (family) empty, XCN.3=Balandan, XCN.4=Paola. `parser.service.ts` L172-173 reads XCN.2 as last name and
  XCN.3 as first name, which is exactly why 7126's error string was `customer_not_found=Balandan`
  (message = `${first} ${last}`.trim(), L179/L192). NPI is in XCN.1 so ordering is not blocked; the provider
  name we read is wrong. Correct form `1730269200^Balandan^Paola^^^^^^N`. Trailing `N` currently lands in
  XCN.9 (assigning authority); `obrSourceTable` reads XCN.8 (`obr-parser.service.ts` L131) and gets ''.
- **OBR-7 = 202609141151, 7 days before MSH-7 (202609212151).** `parser.service.ts` L259 assigns
  `sampleCollectionTime` from each OBR unconditionally, so a backdated OBR-7 becomes the sample's collection
  time verbatim. Empty OBR-7 would default to now (`obr-parser.service.ts` L117-119).

**Sent but never consumed (no impact, but do not assume it arrived)**
- FASTING/NON-FASTING is in **OBR-26**; we read **OBR-19** (`obr-parser.service.ts` L132). Moot either way:
  `fastStatus`, `obrActionCode`, `obrSourceTable`, `obrBatteryText` only populate the OBRHL7 DTO --
  grep shows zero downstream consumers in emr-v2.
- PID-3 UUID is ignored; external id is read from **PID-2** (L138) and patient identity is
  (customer, first, last, gender, dob) via `findByFullNameAndGender`.
- DG1 per-OBR association is flattened: `collectDg1Codes` walks every DG1 in the message into one list.
  DG1-1 starting at 0 and DG1-3 without a coding system are both harmless (only CE.1 is read).
- MSH-5/MSH-6 = `IN OFFICE`/`LC` are receiving application/facility; unread by us (MSH-4 only matters for
  PracticeFusion, `obr-parser.service.ts` L167-171). "IN OFFICE" looks like a draw-location value stuffed
  into the wrong field -- ask the vendor what they meant.
- OBR-11 `N` is not a valid specimen action code; OBR-15 `0`; MSH-12 2.5 vs integration hl7_version 2.3. None read/blocking.

**Next gate after the codes are fixed**
- IN1-2 = `C` -> `ChargeMethod.CUSTOMER_PAY` (`parser.service.ts` L588-590), i.e. the practice is billed.
  JAG's EMR-ordering payment method is still unconfirmed (open item since 2026-07-27) -- that is what the
  next corrected file will hit. Confirm with JAG in parallel.
- Resend must use a NEW file name (dedup by file name). MSH-10 dedup (`parser.service.ts` L128-135) only
  bites once an emr_sample exists, which it does not here, but a fresh control id is still advised.

**Deliverable**: English reply to Olena drafted at
`drafts/BIOINSIGHTS-devcom-reply-20260923-draft.md` (9 numbered items + optional paragraph about the ~150 unpicked result
files in /incoming/). Not sent -- Leo reviews. The draft commits us to sending the current test catalog,
which still depends on Zhenhe.

### [2026-09-29] THIRD devcom file V00000417.hl7 PARSED CLEAN — first BioInsights EMR order created in prod
Trigger: Olena (devcom) email "We sent another file for review" + renewed ask that Leo chase the compendium owner.
L4 verified 2026-09-29 (prod DB + SFTP live):
- `hl7_file_input` **7196 `V00000417.hl7`**, received 2026-09-25 18:30:05 UTC, `parse_finished=1`, `retry_num=5`,
  `last_error=NULL`, pod `lis-emr-v2-deployment-prod-64c7d7f768-b6l5v`, archived to
  `/EMR_storage/HL7Message_prod/BIOINSIGHTS/Prod/Order/archive/` and to `/outgoing/archive/` on the vendor server.
- **Order really placed**: sample_id 2642225, accession/julien barcode **2609256344**, patient_id 3286031
  (`coresamplesv2.patient` John/Doe, customer 30248, `patient_ssn=''` — the PID-19 SSN leak is GONE),
  `lis_core_v7.sample` 2642225 exists (collection/received time NULL — no physical sample, as expected),
  `lis_re.order_table` id 30139923543497260: total **570.00**, charge_method **customerPay**, clinic_id 132493,
  source EMR, is_canceled NULL. `lis_emr.emr_sample` 6618, test_input `305,845`, control_id MSG20260925103194C33B9B.
  `lis_charging.transactions` has NO row for payment_id ffac39bb-8d8c-4718-83cb-66565c8baae7 (no card captured).
- Raw file (pulled from `/outgoing/archive/V00000417.hl7`): **all 9 items from the 09-23 audit are fixed** —
  `VAREQUISTION463^Gut Zoomer 5.0^L` + `VATEST70^Vitamin D, 25-OH^L`; XCN now `1730269200^Balandan^Paola^^^^^^N`
  (family/given land where we read them); OBR-7 empty (defaults to now, no backdating); email moved PID-19 -> **PID-20**.
  Unchanged and still non-blocking: MSH-5/6 `IN OFFICE`/`LC`, MSH-12 2.5, OBR-11 `N`, OBR-15 `0`, FASTING in OBR-26.
- **IN1-2 = C -> customerPay**: the practice-billing gate is now not theoretical — JAG has a live $570 test order
  against clinic 132493. JAG's EMR-ordering payment method is STILL unconfirmed (open since 2026-07-27).
  Decision needed from Leo: cancel/void this test order or leave it.
- No fourth file exists: `/outgoing/` is empty apart from `archive/` (live SFTP check), and no BIOINSIGHTS row in
  `hl7_file_input` after 7196. "Another file" in the email = V00000417 (sent 09-25). Nothing is waiting on us to fetch.
- Quarantine: id 14 (V00000416) went **EXPIRED** 09-29 14:00 UTC on its own. Today's open quarantines 15/16/17 are
  MDHQ `VAREQUISTION471`, unrelated.
- `/incoming/` still holds **153 result .hl7** files (latest by name 2609116512, Sep 11) that the vendor has never
  picked up — result consumption on their side is still not happening. Separate from the compendium.
- **Real remaining blocker is the compendium (test catalog w/ CPT+LOINC) from Zhenhe Zhang** — devcom has asked
  three times. Per the 09-24 rule, it stays *his* open item in any external reply; we do not attach our timeline to it.

### [2026-09-29] Leo 定版了給 devcom 的回信 — 語氣規則（distilled 2026-09-29 -> leo-working-rules.md 09-29 段 + ~/.claude/CLAUDE.md「替 Leo 起草對外文字」）
Leo 把 agent 草稿改寫成他自己的版本並指示「記住我的語氣」。定版全文在
`drafts/BIOINSIGHTS-devcom-reply-20260929-draft.md`（含逐項刪改對照）。抽出來的規則：
- **不慶祝、不報里程碑**：「This is the first order that has ever come through ... ordering side is now
  proven: file pickup, provider lookup, test mapping, patient creation and order creation all work」整段
  被換成五個字 **"The flow looks good to go."** 不列我們內部 pipeline 的每一站，不寫 "Good news:"。
- **不複述對方修好了什麼**：「Every point from my previous email has been applied correctly. For the record: 1-4」
  整段刪。也不寫我們怎麼查證的（"I checked the created patient record: the email is no longer written into
  the SSN field"）。對方知道自己改了什麼，我們的查證過程是內部回報的內容，不是對外信的內容。
- **給他該做什麼，不給我們怎麼分支**：IN1-2 那段的兩行 mapping 表（C -> customerPay / 其他 -> patientPayLater
  + 付款連結）被刪，只留「你送的是 C，這筆算在 JAG 頭上，請確認；要改成病患付就送別的值（P）或整段不送 IN1」。
  事實 + 可執行的替代做法，機制不外流。
- **不安排對方的測試節奏**：「keep using the test patient / let me know before you run any larger batch」刪掉。
- **@ 擁有者就好，不替他說話**：compendium 只留一行 `On the compendium: @Zhenhe Zhang please offer help, thanks.`
  不重述 devcom 要什麼、不解釋為什麼、不安慰對方說這不擋他們。
- **不刪的界線**：agent 標成 optional 的 /incoming 153 個未取 result 檔那段，Leo **保留**。判準是歸屬——
  連線有一半沒啟動是我們該講的事實；對方測試量怎麼抓不是。
- 精確度只給對方用得到的：「We received it on 25 September」保留，「at 18:30 UTC」刪。
延伸自 09-24 已記的「vendor email 只回答被問的那一題 / 不幫別人背書」，這次補的是**長度與姿態**：
結論先給、五個字能講完就不要五行、不回顧、不解釋內部機制、不指導對方做事。

### [2026-10-01] JAG noticed the John Doe test order + charge in their portal — asked why their account is used to test BioInsights
- JAG message (via Leo): lab order + charge for "John doe" not placed by their staff, no phone/address for kit shipping,
  Vitamin D + Gut Zoomer. = devcom's V00000417.hl7 test order (accession 2609256344, $570 customerPay, clinic 132493).
- Prod re-verified 2026-10-01 (lis_emr): BioInsights row cms3icsz700010xlgywfuj8do (vendor 46) still customer 30248 / clinic 132493 /
  effective_npi 1730269200, FULL_INTEGRATION LIVE, ordering_enabled=1, kit_delivery_option NO_DELIVERY (no kit ships);
  sibling P2P row cmjxaqui500i50xfq4zc5yddg (vendor 4, RESULT_ONLY, clinic_name "JAG Consulting, LLC"). Only 3 BIOINSIGHTS
  hl7_file_input rows ever (7126/7154/7196); 7196 is the only parsed one. Could NOT re-check lis_re.order_table is_canceled today
  (lis_emr / lis_frontend_service users lack SELECT on lis_re); last known 09-29: not canceled, no charging transaction.
- Why JAG: the mapping is exactly what BioInsights (Serdar, 07-27) gave us — Office JAG Holdings Group, LLC / Provider 30248 /
  Practice 132493 — and we told devcom (09-18) to put 1730269200 in ORC-12 because it is the only NPI on the integration.
  Every devcom test file will keep landing in JAG's account (and billing JAG when IN1-2=C) until the mapping is moved or
  ordering is paused on that row.
- Deliverable: `drafts/BIOINSIGHTS-jag-mapping-reply-20261001-draft.md` (Leo's voice: mapping listed, ask for the correct
  provider/practice). Decisions left to Leo: void order 2609256344 or not (bracketed sentence), CC BioInsights, and whether to
  set ordering_enabled=0 on the BioInsights row until the correct mapping arrives.

### [2026-10-02] Leo: "done" — JAG mapping reply sent
- Leo replied "done" to the 10-01 draft, taken as: the reply to JAG went out. Not stated: whether order 2609256344 was voided,
  whether BioInsights was CC'd, or whether ordering was paused on the BioInsights row. Prod not re-checked. Waiting on JAG for
  the correct provider/practice before any ehr_integrations change.

### [2026-10-13] Britney (Vibrant Wellness CAM, Florida) re-asks on JAG's behalf: how did JAG get associated / how was their NPI used
- Britney forwarded JAG's 10-01 complaint again (4 screenshots, not in memory) and asks "how they got associated in this integration or
  how their NPI number was used? I see that you all mentioned them first." = JAG does not accept that the mapping came from BioInsights.
- Prod re-verified 10-13 (lisportal ro): BioInsights row cms3icsz700010xlgywfuj8do unchanged since 07-27 (30248/132493/1730269200,
  FULL LIVE, ordering_enabled=1, NO_DELIVERY). Still only 3 BIOINSIGHTS hl7_file_input rows (7126/7154/7196). Ordering was NOT paused
  after 10-02; order 2609256344 void status still unverifiable from here (lis_re no SELECT).
- Answer to "who mentioned JAG first": Serdar (BioInsights) 2026-07-27 email gave Office JAG Holdings Group, LLC / Provider 30248 /
  Practice 132493; we then told devcom on 09-18 to use 1730269200 because it is the only NPI on that integration row.

### [2026-10-13 12:30 PT] ROOT CAUSE FOUND in Outlook: JAG was never a BioInsights practice -- cross-thread mix-up on our side
- Two threads were conflated on 07-27: (1) BioInsights SFTP thread "Integration with Vibrant Wellness" (Kristine/Mingxi/Serdar, May-July,
  no practice ever named); (2) Zendesk "[Vibrant Wellness] Re: Integration" where Britney asked 07-23/24 about Canvas Medical using HTTP(S)
  and on 07-27 sent "Integration Details: JAG Holdings Group, LLC / Provider 30248 / Practice 132493", CC Payton Smith @ Canvas Medical.
- Leo's 07-27 reply in thread (2) described the BioInsights SFTP setup as JAG's integration; the 07-29 Zendesk follow-up still called it
  "the Canvas integration" and asked about replacing P2P (unanswered). Canvas Medical never emailed us (0 mails from canvasmedical.com).
- First mention of JAG inside the BioInsights thread is ours (Keith 09-15, Leo 09-18 NPI instruction) -> devcom test orders carry JAG's NPI.
  Britney's "I see that you all mentioned them first" is correct.
- Thread state (Outlook): Leo 10-01 only "Looping @Mingxi"; Mingxi 10-01 asked BioInsights to confirm the test order; Britney follow-ups
  10-02/05/07 ("Why was Jag Mapping information provided?"), Kristina Banister (Dir. Sales) escalated 10-07, Zhenhe forwarded Mingxi's text
  to Kristina 10-07, Britney re-sent Mingxi's question to BioInsights 10-12 and 10-13, then 10-13 18:09 asked Leo directly. The 10-01 draft
  reply to JAG ("mapping BioInsights gave us") was NOT sent and was factually wrong -- do not reuse it.
- Deliverable: Outlook reply-all draft on Britney's 10-13 email (To Leo/Keith/Kristina), id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABhzr73gAA,
  mirrored in drafts/BIOINSIGHTS-britney-jag-origin-reply-20261013-draft.md. Not sent.
- Prod still unchanged: BioInsights row cms3icsz700010xlgywfuj8do LIVE, ordering_enabled=1, customer 30248. The draft says we are removing
  JAG from the connection -> that change (ordering_enabled=0 / retire row) must be done via lis-prod-change-gate before sending, or reworded.
  Order 2609256344 void status still unknown (no lis_re access).
- Lesson (for dream): an "integration details" email must be matched to the thread/vendor it arrived in, not to whichever onboarding is
  in flight that week. Memory recorded "Serdar thread" for an email Serdar never sent; the L4 check on 10-01 verified the DB row, not the email.

### [2026-10-13 11:31 PT] PROD CHANGE DONE: BioInsights row for JAG retired (LIVE -> REJECTED) on Leo's instruction
- `ehr_integrations` cms3icsz700010xlgywfuj8do: status LIVE -> REJECTED, ordering_enabled 1 -> 0, result_enabled 1 -> 0,
  last_modified_by=Leo, updated_at 2026-10-13 18:31:10Z. `ehr_integration_status_history` id 218 (changed_by BIOINSIGHTS-onboarding,
  reason records the Canvas-thread mix-up). Single tx via emr-v2 .env DATABASE_URL + mysql2 (lock_wait_timeout=5, FOR UPDATE precheck,
  in-tx verify, 1-minute scope check), runner in session scratchpad `reject-bioinsights-jag.js`.
- Why status and not just flags: order side (customer-detail-fetcher `resolveOrderingIntegration`, shortcut.service) gate on
  status=LIVE AND ordering_enabled; kafka report_finished listener gates on LIVE AND result_enabled; but manual repush
  `validateEmrIntegration` is LIVE AND (result_enabled OR type RESULT_ONLY/FULL) -> flags alone would not stop a manual repush.
  REJECTED is the LTM removal-playbook convention (LBS-1833 / VP-18243 same shape). Reversible: set status back to LIVE.
- Readback through the independent read-only host (lisportalprod2 MCP): row REJECTED/0/0; reverse audit over customer 30248,
  vendor 46, NPI 1730269200 (effective + customer_npi) finds no other BioInsights row; exactly 1 row updated after 18:25Z.
- JAG's legit path untouched: P2P row cmjxaqui500i50xfq4zc5yddg still LIVE RESULT_ONLY result_enabled=1 -> results keep going to
  /public/ as before 07-27. Double delivery to BioInsights /incoming/ is now stopped.
- Still open: (1) ~153 JAG result .hl7 files already on BioInsights' SFTP /incoming/ (last counted 09-29) -- delete + ask vendor to
  confirm no copies; (2) void order 2609256344 / $570 (lis_re access needed); (3) send the Britney draft (wording updated to past
  tense); (4) tell devcom to stop using NPI 1730269200 and get a real practice from BioInsights; (5) Canvas question to Britney.

### [2026-10-13 11:35 PT] Britney reply SENT by Leo (18:29:48Z) -- 80 s before the prod row was retired (18:31:10Z)
- Leo sent the first Outlook draft unchanged (To Britney, Keith, Kristina Banister; internetMessageId
  <IA2PR22MB5423ECEA8B5408A1D64C3C90F29E2@IA2PR22MB5423.namprd22.prod.outlook.com>). Its "Removing JAG from the BioInsights connection"
  became true at 18:31:10Z. Bracketed "[Voiding the 25 September test order and the charge.]" went out as-is -> the void is now a
  commitment to Britney; order 2609256344 still needs someone with lis_re access.
- Agent's second (past-tense) draft created 18:32Z was a duplicate; deleted from Drafts. Local draft file is the record.
- Open items unchanged: void 2609256344; delete ~153 JAG result files on BioInsights /incoming/ and get vendor confirmation; tell devcom
  to stop using NPI 1730269200 and get BioInsights' real practice; Britney to answer the Canvas question.

### [2026-10-13 12:00 PT] Britney replied (18:40Z) -- JAG stays on P2P, no Canvas; wants full separation confirmed. Ground truth for the cleanup plan
- Britney: ensure none of JAG's info is linked to BioInsights (patient / billing / account); JAG will NOT do Canvas, keeps the existing
  integration unchanged; reach out to BioInsights directly for the ordering provider -- she suggests portal account 50243 (Travis Bond),
  verify with BioInsights first; confirm once patient info, billing info and all BioInsights-related info/access are removed from JAG's account.
- Verified prod (lisportalprod2 ro, lis_re readable today):
  - lis_re.order_table id 30139923543497260 / sample 2642225 / customer 30248 / clinic 132493 / patient 3286031: total 570 customerPay,
    is_canceled NULL, note "Post Order fail", source EMR. (Same `id` also appears on an unrelated sample 2642226 customer 17909 -- id is
    not unique; ignore, not ours.)
  - lis_charging.transactions 447178: sample 2642225, amount 570, status "1", charge_type testorder, created 09-25 18:30:12Z. customer
    30248 has customer_payment_method NULL. Status semantics unknown to me -> billing team to confirm whether money moved.
  - lis_emr.emr_sample 6618 (sample 2642225, BIOINSIGHTS, V00000417): result_received 0, result_sent 0 -> no result ever produced.
  - BioInsights SFTP /incoming/: **200** JAG result .hl7 files (Jul 16, Aug 99, Sep 38, Oct 47; latest 2610076669.hl7 2026-10-13 01:31)
    -- double delivery ran until the row was retired today. /outgoing/archive/ holds the 3 devcom test files + vibrant_test.txt.
  - lis_core_v7: customer 50243 = Travis Bond MD, NPI 1467734558, clinic 153491 "Bioinsights", signed up 2026-04-27, order_placement_allowed=1.
    customer 30248 = David LeMay MD, NPI 1730269200, clinics 132492 (David LeMay_NPI) + 132493 (JAG Holdings Group, LLC).
    No ehr_integrations row exists for 50243.

### [2026-10-13 12:10 PT] STEP 1 DONE: 200 JAG result files deleted from BioInsights SFTP /incoming/ (Leo: "全部都做")
- Before: 200 .hl7 + vibrant_test.txt. `rm /incoming/*.hl7` -> 200 "Removing" lines, 0 other output. After: 0 .hl7, only vibrant_test.txt
  (our 07-23 probe file, left in place). Listing before/after saved: storage/evidence/BIOINSIGHTS-incoming-cleanup-20261013.txt.
- Originals remain on our side (result pipeline); nothing of ours lost. Vendor-side copies/backups still need BioInsights' written confirmation.

### [2026-10-13 12:15 PT] STEP 3 drafted: Outlook reply-all draft on the BioInsights thread (Britney's 10-13 13:13Z mail)
- Draft id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABhzsABAAA; To Britney + Mingxi/Paola/Lisa/Travis/Serdar,
  CC Olena (devcom), Keith, Kristina. Asks: confirm ordering provider (proposes 50243 Travis Bond / NPI 1467734558) and written
  confirmation that nothing from /incoming/ was retained. Not sent -- Leo sends.
- Step 5 closeout to Britney pre-drafted at drafts/BIOINSIGHTS-britney-closeout-20261013-draft.md; blocked on step 2 (order cancel +
  charge reversal, lis_re / lis_charging -- not in agent write scope).

### [2026-10-13 12:20 PT] STEP 2 handed off: Slack DM SENT to Mingxi (Leo: use Slack instead of email) asking to cancel order 2609256344 / reverse txn 447178
- Slack DM U02RHM3UQ1L, https://vibrantamerica.slack.com/archives/D08MREH9LA3/p1791917771506739 (sent 2026-10-13 ~19:36Z). The Outlook draft to Mingxi was deleted. Agent has no write path into lis_re / lis_charging.
- State of the plan: 1 DONE (files deleted), 2 handed off (Mingxi), 3 drafted (BioInsights ask, Outlook), 4 waits on BioInsights reply,
  5 pre-drafted (closeout to Britney), 6 closed (Britney: no Canvas, P2P stays).

### [2026-10-13 13:00 PT] Retrospective written (Leo: "這是嚴重的錯誤，請你檢討") -> INCIDENT-20261013-bioinsights-jag-crossmap
- Mingxi is handling the order cancel / charge reversal (Leo: "mingxi 去聯繫了").
- Full error chain (10 links), impact (200 PHI files, $570, 12-day delay) and 8 candidate rules recorded in
  storage/short_term_memory/INCIDENT-20261013-bioinsights-jag-crossmap.md. Flagged to Leo: the PHI disclosure needs a
  compliance assessment, not only an engineering closeout.

### [2026-10-13 13:10 PT] Leo: BioInsights Outlook draft is with him; Chinese follow-up to Mingxi NOT sent (dropped)
- Standing rule (Leo): Mingxi in Chinese from now on, short and informal; every outgoing message shown to Leo before sending.
- Plan state: 1 done, 2 with Mingxi, 3 draft with Leo, 4 waits on BioInsights, 5 pre-drafted, 6 closed.

### [2026-10-14 15:00 PT] STEP 2 DONE by Zhenhe/Mingxi: order cancelled + refund issued; BioInsights ask SENT by Leo 10-13; closeout draft ready but gated
- Leo sent the BioInsights provider-confirmation mail 2026-10-13 19:09Z (To Britney + BioInsights team, CC devcom/Keith/Kristina). No reply
  from bioinsights.com or devcom yet.
- Britney 10-14 12:38Z: "We still see this order on the portal". Leo 17:51Z asked Mingxi/Zhenhe for the refund status. Zhenhe 21:16Z:
  order canceled, refund initiated; 21:26Z "@Leo Canceled".
- Prod verified: order_table 30139923543497260 is_canceled=1; transactions 1008956 type=refund $570 card ****8527 created 10-14 16:32Z
  (original 447178 still refunded=0 -- the flow records a refund row, does not flip the flag).
- coresamplesv2.patient 3286031 John Doe (customer 30248, created 09-22 by V00000416) is still isActive=1. Leo 10-14: leave it, no
  deactivation. Closeout item 1 reworded: order cancelled, record holds no real patient data; no removal claimed.
- Closeout Outlook draft created on Zhenhe's 21:26Z mail (reply-all), final wording, mirrored in
  drafts/BIOINSIGHTS-britney-closeout-20261013-draft.md ; ready for Leo to send (draft recreated 10-14 with the reworded item 1).

### [2026-10-14 15:50 PT] CLOSEOUT SENT by Leo (21:46:03Z) -- JAG side closed. Session handoff state
- Sent reply-all (To Zhenhe, Britney, Keith, Kristina, Mingxi), internetMessageId
  <IA2PR22MB54235AEFED082CD2BD0C213CF29D2@IA2PR22MB5423.namprd22.prod.outlook.com>, wording = drafts/BIOINSIGHTS-britney-closeout-20261013-draft.md.
- Plan: 1 done (200 files deleted 10-13), 2 done (order cancelled, refund txn 1008956 10-14), 3 sent by Leo 10-13 19:09Z, 5 sent 10-14, 6 closed.
- OPEN, all waiting on BioInsights: (a) reply to the provider-confirmation mail (proposed 50243 Travis Bond / NPI 1467734558);
  (b) written confirmation nothing retained from /incoming/ -> forward to Britney (promised in closeout item 3).
  Then step 4: new ehr_integrations row for 50243/153491 via lis-prod-change-gate incl. Gate 1b (provenance: the BioInsights reply
  itself), then tell devcom to resend with NPI 1467734558 under a NEW file name.
- Vendor 46 currently has no LIVE integration row; inbound files quarantine as customer_not_found. Patient 3286031 John Doe stays as is (Leo).

### [2026-10-15 PT] Olena 10-15 reply: our 09-23/09-29 field notes contradicted OUR OWN spec; new provider = Aimee Duffy NPI 1528033081
- Leo shared `UpdatedExampleOrder_Explained.pdf` + `HL7_Technical_Reference.docx` with devcom on 2026-09-04 (thread mail). That spec (EMR-Backend origin)
  literally specifies MSH-5 `IN OFFICE` ("Standard for Vibrant"), MSH-6 `LC` ("Always LC"), MSH-12 `2.5`, OBR-11 `N`, OBR-15 `0`, fasting in OBR-26.
  The 09-23 audit and 09-29 reply flagged all of these as wrong/invalid -> devcom pushed back citing the doc. They are right.
- Root cause (agent): audits used parser code as the only reference; the spec we handed the partner was never recorded in STM and never diffed.
  Lesson: before telling a partner a field is wrong, diff their file against the spec WE gave them; spec-vs-code gaps are ours (OBR-26 vs parser OBR-19 is one, harmless today).
- Open asks from Olena: (1) where "draw location" goes -> no HL7 field; kit delivery is per-integration-row `ehr_integrations.kit_delivery_option` (Zhenhe said same to Prospera 10-12);
  (2) requisitions -> order-time Order Summary PDF exists (VP-18138, `ehr_vendors.sftp_order_forms_path`, only vendor 44 enabled), needs a folder on their SFTP;
  (3) clinical catalog details (panel/element/CPT/ref ranges) -> Zhenhe, first asked 10-05, unanswered; (4) provider = Aimee Duffy MD NPI 1528033081 (NOT Travis Bond 50243) -- Vibrant account not yet verified (vibrant MCP down);
  (5) "a person downloaded the file, confirmed deleted" -> one person DID download from /incoming/ (JAG PHI). Britney 10-15 13:28Z asks if a formal notice to JAG is needed, 21:09Z follow-up. Unanswered.
- Leo correction (10-15): Duffy is NOT in ehr_integrations; do not promise "we will register". New provider = full onboarding (Vibrant provider account,
  clinic/practice, integration type, kit delivery, billing) owned by Mingxi + Keith -> loop them in, they collect the info. Agent only executes the row after that.
  Internal note for them: vendor 46 BIOINSIGHTS is still is_public=0, so a portal self-serve integration request may not list it.
- 10-15: Britney reply drafted per Leo (honest to JAG: another clinic downloaded a file, deleted as JAG not their client, NDA in place). Outlook reply-all
  draft on Britney 21:09Z mail, id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABhzvxuwAA. Not sent. NDA existence = Leo's statement, no record in thread/memory.
  Download count still "a file" per Olena's wording; unconfirmed.
- 10-15: Olena reply drafted in Outlook (reply-all on her 07:50Z mail), id AAkALgAAAAAAHYQDEapmEc2byACqAC-EWg0AJgEEG39__0mH_2569j02fwABhzvxywAA.
  To Olena/Zhenhe/Mingxi/Keith; owners: Duffy onboarding = Mingxi+Keith, test details = Zhenhe. Requisition line still says "yes" (prod enablement not yet approved by Leo). Not sent.
- 10-15 Leo's final Olena reply (he sends it himself) vs agent draft: opened with "Thanks for the confirmation." and DROPPED "You are right, those values
  follow our document" (no conceding line); onboarding owner = Mingxi only (Keith removed); Zhenhe line = "confirm the order detail, and let us know in this
  thread if there is anything blocking you"; DROPPED the "how many files were downloaded" question -> download count stays "a file" (Britney draft relies on it).
  Requisition line kept as "yes ... we can ... which folder" -> enabling vendor 46 `sftp_order_forms_path` (currently NULL, verified prod 10-15) is now a commitment once they name a folder.

## Retrospective 2026-10-15 (Leo: "這個 ticket 你犯了非常多的錯誤，請檢討")
Errors on the devcom side of this ticket (JAG cross-map itself is in INCIDENT-20261013-bioinsights-jag-crossmap):
1. 09-23 / 09-29 field audits judged devcom's file against parser code only. We had sent them UpdatedExampleOrder_Explained.pdf +
   HL7_Technical_Reference.docx on 09-04; that spec mandates MSH-5/6/12, OBR-11/15, OBR-26 exactly as they sent. We called our own spec "invalid".
   Root: the shared spec was never recorded in STM, so the audit had no partner-facing reference. Invariant: a partner file is judged against
   the spec WE gave them; spec-vs-code gaps are ours (OBR-26 vs OBR-19 still open).
2. 10-15 first answer built from the pasted mail only. Did not read the Outlook thread -> missed requisition ask (open since 10-06),
   clinical-details ask to Zhenhe (open since 10-05), Britney's two 10-15 mails. Violates core principle 0 (sync with the world first).
3. Asked Leo "do we generate requisitions?" when VP-18138 (built by this agent, in LTM) answers it, and prod could be read. Questions to Leo
   only after memory + ground truth come up empty.
4. Draft promised "we will register Dr. Duffy" without checking ehr_integrations or knowing the onboarding owner (Mingxi/Keith). Same family as
   INCIDENT R1: we do not promise actions whose preconditions and owner we have not verified.
5. Put "[TBD]" inside the first outgoing draft -- INCIDENT R7 (written 10-13) re-violated 2 days later. Prose lesson did not hold.
6. Draw-location and requisition sentences written from partial knowledge: DBS (test-code) dimension omitted; "we can" implied new dev while the
   feature exists and only vendor 46 enablement is missing. Every claim about our system must be checked (code/prod) before it is written.
Common root: reference = our own memory/code instead of what the counterparty actually has (their thread, the docs we sent them, prod state).
Prevention proposed to Leo (pending approval, automation -> PR):
- P1 vendor-email-reply checklist (skill): read full thread incl. our sent mails -> list unanswered asks w/ date; list docs shared with the
  partner; diff partner files vs that spec; verify each factual claim; each promised action has a named owner + verified precondition.
- P2 PreToolUse hook on Outlook draft/send tools: reject bodies with [TBD]/[...]/TODO placeholders (R7 -> enforced).
- P3 keep partner-facing specs in repo (knowledge/partner-specs/) + a spec-vs-parser gap table; STM "Shared with partner" section per onboarding.
- 10-15 retro follow-through: P2 hook merged (factory #97, wiring #58; push-guard repo-resolution bug found + fixed factory #98).
  P1+P3 = PR #59 (skill vendor-email-reply, reference/partner-specs/ + gap-table). Gap table found spec-level errors: IN1-2 "C=Commercial"
  vs code C=customerPay; spec example codes VAREQUISTION279/VATEST2270 wrong (devcom copied them); XCN comp2 = internal id in spec vs parser last name.
  HL7_Technical_Reference.docx not located in SharePoint.

## Open items (go-live checklist)
1. ~~BLOCKER: provision account permissions~~ DONE 2026-07-23 (Serdar). Remaining vendor asks: confirm direction convention (incoming/outgoing semantics) + sample HL7 files.
2. Scope unclear: orders inbound only, results outbound only, or bidirectional? Which practices/clinics? (drives ehr_integrations rows — order gate is ehr_integrations LIVE+ordering per VP-16968 cutover)
3. ~~ehr_vendors row~~ DONE 2026-07-23 (id=46, is_public=0 — flip at go-live). ~~sftp_folder_mapping~~ DONE (id=281, cloud). STILL PENDING: ehr_integrations per practice (needs scope from #2).
4. Need sample HL7 files from vendor to decide transformer mapping needs.
5. Move/secure the private key (unencrypted in ~/Downloads); consider filing a VP ticket for tracking.

### [2026-09-24] Lisa Bond (BioInsights CPO) asked for a status update — Leo's rule: do not vouch for other people
- 09-24 05:17 Lisa Bond (CPO, BioInsights) emailed Britney + Leo, cc Travis, asking where the integration
  stands, what is holding it up and what the next steps are. Forwarded on top of Leo's 09-23 reply to Olena
  (the 9-item field audit of V00000416.hl7) and Olena's 09-23 note that devcom is blocked on the compendium
  from Zhenhe Zhang.
- **Leo's instruction (verbatim): 「不幫她背書，只要回答工程的等待正確 hl7 就可以」** — the reply answers ONLY
  the engineering state we own: the integration is in HL7 order-file testing and is waiting on one thing,
  a corrected test file from devcom, resent under a NEW file name and a new MSH-10 (dedup by file name).
- First draft was rejected for two things that were not ours to say:
  - it carried "we are sending Devcom our current test catalog" — the compendium belongs to Zhenhe and has
    no committed date, so saying it in our voice converts his open item into our promise (the same flaw was
    already noted in the 09-23 devcom draft: "commits us to sending the current test catalog, which still
    depends on Zhenhe");
  - it asked Lisa to chase JAG on billing (IN1-2 = C) and to nudge devcom — real next gates, but making them
    the customer's homework in a status reply reads as apportioning blame and expands the answer past what
    was asked.
- Generalized rule for external email in this workspace: state only facts our side observed (files received,
  what parsed, what blocked, what we need back) and the one thing the project is waiting on. Another team's
  or another company's deliverable gets mentioned only as their open item, never with our timeline attached,
  and never with a request routed through a third party. Leo: this is Vibrant-Wellness-level knowledge, to be
  kept — home is `leo-working-rules.md` (external communication), pending dream distillation.

### [2026-10-26] Olena 10-26 15:14Z "we are currently blocked" (to Mingxi); Mingxi 19:45Z told Britney (CAM) to start onboarding via Support, no IT needed
- L4 10-26: Aimee Duffy NPI 1528033081 has NO lis_core_v7.customer account at all (only Michele/Sarah Duffy, other NPIs). BioInsights vendor 46 has only the REJECTED JAG row; zero LIVE integrations.
- So the chain is: Vibrant account for Dr. Duffy -> integration created on Website -> devcom resends test order with new file name. Per VP-18960 rule the agent does not create the integration.
- Still unanswered from Olena 10-15: requisition (order summary PDF) folder (her side to tell us); per-test catalog details (Zhenhe).
