---
id: rules
type: ltm
category: pm_patterns
status: active
score: 0.1673
base_weight: 0.8
urgency: 3
created: 2026-10-15
updated: 2026-10-15
links:
- INCIDENT-20260518
- INCIDENT-20260529
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260604-mdhq-stale-connections
- INCIDENT-2604156666
- LBS-1773
- LBS-1784
- LBS-1785
- LBS-1799
- LBS-1828
- NEXTECH-onboarding
- PO-270
- SANDBOX-SEED-W2W-20261005
- VP-16514
- VP-16921
- VP-16934
- VP-16945
- VP-17344
- VP-17497
- VP-17499
- VP-17524
- VP-17584
- VP-17591
- VP-17628
- VP-17685
- VP-17748
- VP-17766
- VP-17827
- VP-17868
- VP-18034
- VP-18048
- VP-18050
- VP-18055
- VP-18085
- VP-18138
- VP-18194
- VP-18270
- VP-18288
- VP-18303
- VP-18342
- VP-18344
- VP-18372
- VP-18402
- VP-18404
- VP-18406
- VP-18463
- VP-18481
- VP-18589
- VP-18593
- VP-18714
- VP-18749
- VP-18782
- VP-18796
- VP-18833
- VP-9299
- ticket-routing
tags:
- rules
- constitution
- feedback
- auto-generated
summary: Auto-aggregated constitution from 117 rule-bearing paragraphs across STM
---

# Rules / Constitution

> 自動萃取自所有 STM 的 `## User Feedback` / `## Lessons Learned` / `## Decisions Made`
> 段落中含 imperative 語氣或 Leo 明確指令的句子。
> 由 `scripts/extract-rules.py` 維護，下次 run 會覆蓋。
> Last updated: 2026-10-15 — total 117 rules across 8 categories

## Categories

- [Git / branch / commit / push](#git-workflow) — 56 rules
- [Scope / requirement / PM communication](#scope-comm) — 33 rules
- [Other / uncategorized](#other) — 9 rules
- [Production safety / kafka / email / SFTP](#prod-safety) — 9 rules
- [Error handling / throw / log / silent](#error-style) — 6 rules
- [DB / SQL / FK vs derived column](#db-style) — 2 rules
- [Testing / mock / verify](#test-style) — 1 rules
- [Review flow / report format / approval](#review-flow) — 1 rules

---

## Git / branch / commit / push <a id='git-workflow'></a>

### [[INCIDENT-20260518]] · _Decisions Made_

### [2026-05-19] 直接 push staging branch
平常 Leo 規則禁止 push staging，但此 incident 緊急且 Leo 明確兩次授權。

### [[INCIDENT-20260604-mdhq-stale-connections]] · _User Feedback_

### [2026-06-04 ~22:00 UTC] "以後你要 push 要 push 到 staging 不能直接 push 到 main"
Workflow clarification. Updated [[push-triggers-deploy]] memory. Feature branch push doesn't auto-deploy (verified). Staging access is via PR, not direct push.

### [[INCIDENT-20260604-mdhq-stale-connections]] · _Lessons Learned_

### Tool gotchas
- `expect` `spawn` with `"...{stuff}..."`: `{}` are Tcl-significant. Either escape as `\{` or use `{...}` Tcl-literals around the whole command, but mixing `"..."` interpolation with `{}` blows up. Prefer `kubectl --no-headers -o custom-columns=` over `-o jsonpath='{...}'`.
- kubectl pod label selectors ≠ deployment names. Always `--show-labels` first.

### [[LBS-1773]] · _Lessons Learned_

### [2026-09-04]
- Interrupted terminal output != rolled-back transaction. The `--commit` run was Ctrl-C'd after Prisma had committed; always re-SELECT before deciding between "re-run INSERT" and "UPDATE" (a blind re-run would have hit the dup guard, a blind UPDATE with no row would have been a silent no-op).
- Athena practices in prod are mixed: 124546 (14 rows) and most MIGRATION practices use msh06=Provider ID; LBS-1656 (18299), 154911, 125563 use Practice ID. For Athena, Leo chose "follow the practice's existing peers" over the 2026-04-23 Practice-ID default — put the peer convention first in the decision list next time, not the policy.

### [[LBS-1773]] · _Decisions Made_

### [2026-09-03 22:45 PDT / 2026-09-04 05:36Z] Leo
- First reply「填clinic id」-> commit ran with --msh06=124546 (new row only, no --align-practice). Terminal output was interrupted mid-run but the transaction had COMMITTED: ehr_integrations `cmtm3tumy00010xdk8p6gokqk`, order_clients `2337` (05:36:25Z).
- Second reply「follow 那14個填provider id」-> single bounded UPDATE (id + customer_id + clinic_id + old msh06 value) msh06 124546 -> 53041, affected=1 changed=1. 14 peers never touched.
- customer_name 'Lisa Schultz' without suffix (practice peer convention) — not objected.

### [[NEXTECH-onboarding]] · _Lessons Learned_

- Vendor email folder labels ("Export - Orders") are not paths; always `ls` the real tree before writing paths into ehr_vendors.
- **When a human instruction names a vendor/practice that the source document contradicts, the recently-provisioned-but-unused config is the tiebreaker.** MDHQ vs Nextech was settled not by re-reading the email but by noticing vendor 47 had template + folder mapping + zero integrations, created two days earlier — the exact shape of "mid-onboarding".
- **Build a new integration row from the API service code, not from a peer row.** Peer-copying would have produced `pipeline_location='onprem'` (silent dead end — no pod scans the folder), `legacy_emr_service='MDHQ'`, and no `ehr_integration_status_history` row. `IntegrationRequestService.create()` is the spec; peers are only evidence of what defaults people picked.
- The per-practice SFTP folder slug problem is Cerbo/MDHQ-specific (`{folder}` placeholder in the template). Non-Cerbo vendors copy concrete template paths, so "which folder?" is not a question to ask for them — check the template for `{folder}` before asking anyone.
- Correction to a claim made mid-session: `sftp_archive_path` on ehr_integrations is inert (only the configuration-management CRUD reads it), but that does NOT mean the remote `archive/` folder is unused — the fetcher archives via `HL7_REMOTE_POST_FETCH_ACTION` (default `archive`) in `hl7-order-fetch.service.ts`, independent of that column. Two different mechanisms with confusingly similar names.

### [[NEXTECH-onboarding]] · _Decisions Made_

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

### [[PO-270]] · _Decisions Made_

### [2026-10-08 10:10]
- No code change: not an LIS repo, no access to source or cluster. Deliverable = diagnosis + routing + draft Jira comment for Leo.
- Verdict: today's 500 is most likely another transient be-location failure (same class as PO-268: gRPC upstream ECONNRESET / cold restart), not the VP-18313 decommission and not the dead :8019 host. Healthy at 16:50-17:07 UTC: 15/15 201 on www.vibrant-america.com and 15/15 on phleb.vibrant-wellness.com, avg 1.05s, max 1.34s.
- Recommend: (1) route to Michael Kingsley / Jun Zhang with the exact window (2026-10-08 ~14:30-15:30 UTC) to pull be-location logs and check restarts; (2) do not close as Cannot Reproduce a second time without the log pull; (3) separate fix for the frontend's hard-coded `zymebalanz.com:8019` (repoint to `https://phleb.vibrant-wellness.com/app/api/v1/urls`, drop the dead `/agency` link) so the first scheduling-enabled draw site does not take the whole page to /500; (4) ask the owner to ship phleb-system-production logs to Datadog, since every one of these tickets dies on "already recovered by the time I looked".

### [[VP-16921]] · _Lessons Learned_

- **"Prod DB is clean" ≠ "no bug."** Causes that erase/bypass prod evidence: (a) FK ON DELETE CASCADE on audit tables, (b) a SEPARATE environment publishing to the prod email pipeline without writing the prod DB. Always get the customer's real artifact + Postmark send record + the Kafka message before concluding non-bug.
- **Forensic chain for "who sent this email"**: Postmark Messages API (recipient/subject/Metadata/MessageEvents) → find the Kafka message on notification-email-template (Datadog trace headers x-datadog-trace-id / traceparent embedded by dd-trace producer instrumentation) → look up the Datadog producer span → service/env/git-sha/host → host node → cluster. Postmark token lives in `noti/notification-center` pod env `POSTMARK_KEY`.
- **Multiple transv2 deployments all share the PROD notification Event Hub** (`notification-email-template` @ vibrant-notification-events). reminder @Cron is gated ONLY by `platform_type==='local'`. So any non-prod transv2 with platform_type≠local + a calendar DB with due events = real emails to real customers. Governance gap.
- **`listest` is a real AKS cluster** in sub 4dbf30e2 / rg lisportalprod that most accounts can't see (RBAC). It can run rogue services against prod pipelines. When prod evidence is absent but emails are real, suspect listest / other-subscription clusters; identify via the Kafka msg's Datadog trace `host` field.

### [[VP-16921]] · _Decisions Made_

### [2026-06-09 00:23] RESOLVED — root cause confirmed & stopped
- Leo pinpointed cluster via portal: AKS **`listest`** (sub 4dbf30e2, rg lisportalprod). hung.l has NO Azure RBAC on it (`az aks list` filtered it out; show/get-credentials → AuthorizationFailed) — that's why it was invisible. node `aks-agentpool-40220894-vmss000000` belongs to `listest`.
- **Root cause**: `lis-transformer-v2` instance in `listest` (env=test, unpushed build e01adb3) was configured with PROD notification Event Hub (`notification-email-template` @ vibrant-notification-events) + read a STALE calendar DB (Dawn's 6/9 event 10004 never got the 5/22 prod cancellation, still is_canceled=false) → reminder @Cron (not gated, platform_type≠local) sent REAL Postmark reminders (48h 6/7, 24h 6/8) to the real provider.
- **Fix applied**: Leo took down the listest transv2 instance → emails stopped. Confirmed it was the cause.
- prod was always correct (cancelled 5/22); NOT a prod bug.

### [[VP-16934]] · _Decisions Made_

### [2026-06-08] 安全執行原則（Leo 明確要求的 rule）
1. **絕不送任何東西給 customer**：lis-backend-emr-v2 `.env DATABASE_URL` 指 **prod**，finalize 會 charge + sendOrder + email。spike 一律 **dryRun 且 mock 外部 client**（charge/orderTest/email/grpc），不連 prod 不送單不刷卡。
2. **end-to-end 測試**：以 spec test 形式驗證，跑得起來、可重現。
3. **結果完全一致**：VP-16937 用 ground-truth diff，`expect(diffs).toEqual([])`，proto 相同 ≠ marshalling 相同（[[feedback_end_to_end_equivalence]]）。
4. **先建 branch**：`feature/leo/VP-16936`，不 push 不開 PR 直到 Leo review（[[feedback_push_triggers_deploy]] / [[feedback_no_direct_push_to_staging]]）。

### [[VP-17497]] · _User Feedback_

- [2026-07-27] Leo asked whether the DB migration was remembered — it was (applied+verified staging & prod pre-merge), but the question itself signals: always surface the migration status LOUDLY in reports, first line of the deploy section.

### [[VP-17497]] · _Decisions Made_

- [2026-07-27] Leo: Phase 1 (reclaim, no schema) + Phase 2 (failed retryable via stored payment) together, separate commits; docs too.
- Reclaim keeps the row (audit trail) — status-gated atomic updateMany, NOT delete; concurrent resends: exactly one wins.
- failed is dangerous to blindly retry: finalize is charge-first -> a placement failure may strand a completed charge; order_intake had no payment columns to replay. Phase 2 persists the charge immediately after transactionPay returns (before placement outcome known) and passes it through parseOrderInfo so finalize's pre-existing HL7 replay branch (sample_id_payment != null) skips the charge.
- Same placerId must carry the same order payload (documented); payload replaced on reclaim.

### [[VP-17524]] · _Lessons Learned_

### [2026-08-18] RE-CHECK: on-prem redeploy landed — prod verdict was never actually exercised

### [[VP-17524]] · _Lessons Learned_

INCIDENT-20260817-onprem-stale-deploy open item 4: this ticket's behaviour had **never run in
prod on the on-prem path**, which owns 536 of 1036 LIVE result-capable integrations. The on-prem
prod pod was frozen at 2026-08-04 code for 13 days and only redeployed **2026-08-18 18:33Z**
(uptime 13,251s measured during the VP-17734 session). Re-verify this ticket's behaviour against
an on-prem-owned integration before treating the completed status as prod-proven.

### [[VP-17524]] · _Decisions Made_

### [2026-08-06] Leo on repush: "不用 repush"
Historically mis-delivered results (blank OBX-8 + "Test Not Processed" NTE) will NOT be resent.
Do not open a repush task for this ticket.

### [[VP-17591]] · _Lessons Learned_

### [2026-08-18] RE-CHECK: on-prem redeploy landed — prod verdict was never actually exercised

### [[VP-17591]] · _Lessons Learned_

INCIDENT-20260817-onprem-stale-deploy open item 4: this ticket's behaviour had **never run in
prod on the on-prem path**, which owns 536 of 1036 LIVE result-capable integrations. The on-prem
prod pod was frozen at 2026-08-04 code for 13 days and only redeployed **2026-08-18 18:33Z**
(uptime 13,251s measured during the VP-17734 session). Re-verify this ticket's behaviour against
an on-prem-owned integration before treating the completed status as prod-proven.

### [[VP-17628]] · _Lessons Learned_

- "Unset" for a setting has TWO physical forms here: no row AND empty-string row (37% each of active clinics). Always probe ground truth for the unset SHAPE before coding a fallback guard.
- When two stakeholders give conflicting fallback rules, check if they're ruling on different actor classes — a per-token-type matrix dissolved the conflict.
- Live read-only probe of a new RPC with the repo's own proto (before shipping client code) validates field naming + real data shapes cheaply.

### [[VP-17748]] · _Lessons Learned_

- Blast radius on the emr side is far smaller than PR #921's table implies. The result-push
  path (`result-generation.service.ts:476,636`) reads only `customerId` (4) and `clinicIds` (3)
  from `sampleReleventResponse` — both unchanged. `patientGender` / `patientBirthdate` off this
  RPC are surfaced only by the diagnostic REST route
  `GET /api/v1/grpc-v2/sample/:sampleId/relevant-info` (grpc-v2.controller.ts:89).
  HL7 PID gender/DOB come from the patient service (`patient_service.proto`), untouched here.
- A pure field renumber is breaking in BOTH deploy orders — there is no safe single-side window.
  Against today's deployed coresamples, the synced emr proto decodes the server's
  `patient_birthdate` into `patient_gender` and leaves birthdate empty; against post-#921
  coresamples, an unsynced emr does the accession-id-into-gender misread the PR describes.
  Deploys must be paired; this branch must not go out before #921 is live on the same env.

### [[VP-17766]] · _User Feedback_

### [2026-09-08 19:30Z] Leo asked: accession 2603306653 "Zoom link email not received" case
- Not in Jira (full-text search empty) nor local memory; located via calendar_prod `v2_event.notes`.
- Event 12934, Clinical Consult (Zoom), booked 2026-08-20 17:40Z for 2026-09-04 20:30Z,
  clinician Brooke Ganev (cal 30789), seeker = patient-role cal 34737 (owner 33172 Cleo Tetzloff,
  provider cal 7857 practice 125989). Form typed `saadia@higherstandardwellness.co`; calendar
  snapshot (2026-02-23) = `cleo@cleoameliawellness.com`. All 3 reminders (48h/24h/15m, template
  33802989, the ones carrying the Zoom link) sent to cleo@ -> saadia never received the link.
  Same owner's earlier booking 11443 (2026-06-26, Courtney, courtney@higherstandardwellness.co)
  had the identical mismatch. Textbook VP-17766 case; event already past, nothing to resend.
- Current state: BE deployed 09-08 but va-portal does not send contact_email yet, so this
  account's next booking still goes to cleo@. Options given to Leo: FE follow-up ticket, or a
  bounded single-row interim fix on cal 34737 (owner_email or notification_cc_emails). None executed.

### [[VP-17827]] · _Lessons Learned_

### Technical
- The practice-attribution problem is not "vendors will send a practice ID and we need to read it".
  Measured over ~180 days: five of six active vendors send nothing usable, and the one field that
  looks like a practice id (MSH-4) usually holds the provider's Vibrant account number. Any future
  design must be a layered fallback on top of the existing ORC-12 provider resolve. Replacing the
  resolve regresses live orders — there is a named counter-example (clinic 6212's 2026-08 orders).
- `hl7-order.processor.ts:364-500` already contains a provider-then-practice cascade, but it is
  advisory (logging + provider email) and its practice branch has never fired in production
  (0 rows with `customer_id='-1'` and `ordering_enabled=1`). It is the natural seam for this work,
  but it is a seam, not an implementation.

### [[VP-17827]] · _Lessons Learned_

### Tooling
- Dream pipeline aborted three consecutive nights (08-21/22/23): "ABORT: uncommitted changes to
  tracked memory files — storage/short_term_memory/VP-17812.md". Last good run 08-20, which is
  exactly why every `_index.md` read `Last updated: 2026-08-20`. The guard only inspects TRACKED
  files, so new untracked STM files do not trip it.
  The guard's own comment says "a dirty memory file is a signal, not an obstacle" — but as written
  it is an obstacle with no escalation: one forgotten commit silently stops the entire distillation
  layer for an unbounded number of nights, and the only symptom is a stale date inside a file
  nobody re-reads. The staleness check in CLAUDE.md is what caught it, three days late.
  Down-push candidate (ENFORCEMENT-LADDER): the guard should escalate on repeat — abort once, then
  on the second consecutive abort either notify loudly or run in a read-only/no-write mode, so the
  failure cannot be silent for more than one night.

### [[VP-17827]] · _Lessons Learned_

**Ground truth re-read today (prod lis_emr via AKS prod pod `lis-emr-v2-deployment-prod-cfbbc6b47-q4stq`,
read-only `$queryRawUnsafe`; local MySQL + vendor SFTP + on-prem all unreachable = no VPN).**
- Vendor 44 FOLLOWTHATPATIENT: 33 `ehr_integrations` rows, all LIVE / FULL_INTEGRATION, 32 ordering_enabled
  (46332 off), 20 distinct clinic_id, 30 distinct customer_id. Full list with names:
  `reference/followthatpatient-practice-ids-20261007.csv`. Names came from `order_clients.customer_name`
  (21 of 30); the 9 accounts of the 06-22 batch (30528, 43263, 502816, 523148, 46803, 46535, 48127, 51471,
  51154) have no name anywhere in lis_emr. 502816 / 523148 (clinic 22106) also have no NPI.
- `hl7_file_input` emr_service=FOLLOWTHATPATIENT: 11 orders total, 07-09 .. 10-06. Placed clinic per
  `order_input.clinic_id`: 2930 x6, 8003 x2, 142676 x1; 2 never placed. Shared providers still dominate:
  Anna Emanuel 43262 sits on 4 clinics (2930/8003/36290/144510), Darshan Shah and Jeffrey Egler each have
  one account per location (the clean shape).
- **Open intake failure, not on this ticket:** id 7266 `ORDER_3_13_20261006085448.hl7` (received 10-06
  16:02Z) has `emr_code_not_found=VAREQUISTION471`, parse_finished 0, order_input NULL. Neither
  `DailyJob/hl7_fail/triage_2026-10-06.md` nor `_10-07.md` mentions it. Same class as the 07-09 failure
  (VASC727501). Needs its own look (bug-triage), flagged to Leo in the report.

### [[VP-17827]] · _Lessons Learned_

**Answer to Tom's (a):** yes, intake resolves from ORC-12 only and never reads ORC-17. (b) and (c) are Keith's
(release date = product commitment; re-billing = ops). Draft v1 at
`drafts/VP-17827-prospera-practice-id-reply-20261008.md` hands both to Keith and lists the 5 orders by the
vendor's own order id (ORC-2 / FTP3-n) with ORC-17 vs booked clinic.

### [[VP-17827]] · _Lessons Learned_

**Code facts that shape the design (origin/main c15bb82).**
- `ehr_integrations` rows are already (customer_id, clinic_id) pairs: one row per provider per practice. A
  practice-level resolve needs no new table; `resolveOrderingIntegration` just has to take the practice into the
  WHERE instead of sorting it away. VP-16164 (practice_integrations + memberships, Inactive since 06-15) is the
  PRD's long-term model; not required to fix this.
- Vendor identity reaches the parser as `OrderInfo.emrName` = `hl7_file_input.emr_service` ('FOLLOWTHATPATIENT').
  No per-vendor "which field carries the practice id" config exists anywhere (`ehr_vendors` has none).
- Practice id is already persisted: `order_input.clinic_id` and core `sample.clinic_id` = the resolved clinic. The
  AC "persist practice ID on the order record" is met by resolving to it; no schema change needed.
- PH-917 membership gate (parser.service.ts:228-262) runs after resolve and checks provider in chosen clinic; it
  becomes a consistency check on the practice we picked, no change.
- Advisory MSH-4 cascade in hl7-order.processor.ts:585-605 is a separate, log-only path; leave alone.

### [[VP-17827]] · _Lessons Learned_

Leo: "開pr". Commit `9d1ab62` on `feature/leo/VP-17827`; pre-push hook ran build + 19 related suites (289 tests) green.
PR https://github.com/Vibrant-America/lis-backend-emr-v2/pull/468 targets **`staging`** — emr-v2 has no `stage_test`
branch (`gh` refused: "Base ref must be a branch"); `stage_test` is LIS-transformer's. Per Leo's 2026-10-03 merge rule
(agent PR to staging-class branch: merge, wait deploy, self-test) the next step is merge + staging replay once CI is green.

### [[VP-17827]] · _Lessons Learned_

**Staging topology learned.** AKS `-staging` pod is endpoints-only; HL7 intake + retry-rescan run on the on-prem staging
pod (PIPELINE_LOCATION unset = onprem; staging has zero `pipeline_location='cloud'` folders so ownership `{}` = every
`parse_finished=0 AND retry_num>0` row). `/EMR_storage` is persistent across pod replacements. Staging DB
192.168.60.11 lis_emr, writable from the AKS staging pod via prisma `$executeRawUnsafe` (root). Staging order
placement targets `VIBRANT_API_BASE_URL=…/base-report-dev-service` (dev core): staging sample ids collide with prod
ids from a May-2026 snapshot (2554429 in prod = customer 26162 / clinic 119726, May 13) — never read a staging sample id
against prod.

### [[VP-17868]] · _Lessons Learned_

- Before writing "contact X to fix this" into an error message, find the code path that performs the fix and confirm which role and which UI owns it. The unlock here lives in a different portal than the error.
- An error message that says a resource is "in use" must name the thing using it, or say that finished/past uses still count — otherwise the user searches their live list, finds nothing, and escalates.
- Check write access to a repo before planning work in it: `gh api repos/{owner}/{repo} --jq .permissions.push`. A cross-repo fix can be half-deliverable.

### [[VP-18034]] · _Lessons Learned_

- Source: Slack relayed by Leo 2026-10-14 — Get Healthy registered a prod payment method under
  order-email@gethealthy.store and sent the prod public key; Fangyuan asked if prod also uses 1001; Leo: "prod 用 1001".
- Key is the SAME key as staging 1001 (SPKI DER sha256 d6cec97bc9d3fff2…, 2048-bit RSA).
- Prod lis_emr (lisportalprod2) pre-check: platforms 0 rows, platform_public_keys 0 rows. In one tx:
  platforms ('1001','Get Healthy',active 1,charging_account_id 1001) + platform_public_keys
  ('1001','gethealthy-2026-09', PEM unescaped). In-tx readback 1 row; second connection readback
  1 row total in both tables, stored PEM byte-equal to input. created_at 2026-10-14 17:41:57 UTC.
- Consumer-layer readback, in prod pod lis-emr-v2-deployment-prod-847c9f7956-vs8vn (POST
  /api/v1/order-intake, self-minted HS256, random RSA key): 1001 + kid gethealthy-2026-09 -> 401
  bad_signature (key found and used); 1001 + unknown kid -> 401 unknown_kid; 9999 -> 400 unknown_platform.
  order_intake rows with placer_id VP18034-PRODPROBE-% = 0 (rejected before intake).
- Open: Fangyuan must create prod charging account_type=platform / account_id=1001 with the card
  bound; accounting `account_type=platform` enum on prod (VP-18089 gap #3) not confirmed. Collect-money
  leg only verifiable by Get Healthy's own request (they hold the private key).

### [[VP-18034]] · _Decisions Made_

- L4 re-sync: Xiaoye moved BOTH tickets Dev Blocked → Dev In Progress at 11:42 (3 pts each, due
  09-16) without answering any of the five open questions; VP-18031 (Rui) due pushed to 09-15,
  still Dev To Do, zero comments, no branch in emr-v2/charging/oauth. VP-18089 in QA Review
  since 09-03. Charging main moved 661ce1e → 7c74c58 (#361 VP-17954 payment-method priority
  ordering — GetPaymentMethodsOfCustomer now ORDER BY priority DESC, id ASC, affects the
  platform list order too; #362 LIS-7737 orphan-capture recovery in payWithCardViaStaxV2,
  only on `without_apply`, which emr-v2 never sends). Neither closes the MIT-meta or
  batch-path gaps.
- emr-v2 main moved 582c00d → 87ce490 (14 commits, VP-18085/18095/18138); PR-A rebased clean
  (only .env.example overlapped, additive). PR-A head is now 77ca209.
- Stacking: PR-B lives on `feature/leo/VP-18034`, branched FROM PR-A's head (it imports the
  verifier). One-PR-one-head rule: PR-A goes up first; PR-B's PR is opened only after PR-A
  merges and PR-B is rebased onto that main (its head changes once, before its PR exists).
- Decisions taken without Leo (all reversible, none touch schema):
  - Verify in the CONTROLLER before the intake row (as presented 09-03). Consequence stated in
    code: a resend reusing an assertion is 401 `replayed`, not `duplicate`; a `dryrun`-mode T
    request consumes its jti without charging.
  - No `payer_platform_id` column (DB schema needs Leo's explicit OK). Reconciliation for now =
    `order_intake.request_json` (carries chargeIndicator T + platformId) + the
    `[order-intake] ... paid by platform` log line.
  - `PlatformRecord.chargingAccountId` (optional, falls back to an integer platformId): the id
    Rui issues and charging's integer account_id are separate identifiers; a platform with
    neither is `unchargeable_platform` → 400 INVALID_PLATFORM_ID, checked before any crypto.
  - Pending-batch id (`charging_v2_pending_batch_*`) from charging on the platform path =
    charge NOT completed → paymentFailed, chain stopped (charging already holds a pending
    record for that token). Customer-pay behaviour unchanged (still accepts it, as before).
  - `T` maps to ChargeMethod.CUSTOMER_PAY in ENRICHMENT, not in the mapper — the mapper's
    IN1.2 rule is shared with the HL7 path and an HL7 `T` must keep meaning patientPayLater.
  - Header ignored for C/P/I/O (no 400) — it authorizes nothing but a platform payment.
- Dream pipeline stall diagnosed: 6 nights ABORT "uncommitted changes to tracked memory files"
  (this STM dirty since 09-04, later joined by VP-17766 / INCIDENT-20260908). Indexes frozen
  at 09-03. Fix = commit the memory repo (done this session).

### [[VP-18034]] · _Decisions Made_

- Jenkins rolled ~11 min after merge: staging pod `lis-emr-v2-deployment-staging-544ddb486f-7w6k2`
  image d67f029 (#410 merge), prod pod `lis-emr-v2-deployment-prod-c4549bc86-r96rj` image
  10ecea0 (#411 merge). Both Running, restarts=0, Ready=True, "Nest application successfully
  started", `/app/dist/modules/platform-assertion/` present (5 .js + maps) on both,
  `GET /api/v1/health` 200 (note: `/health` without the prefix is 404 — the health route lives
  under /api/v1). Prod log shows only the usual kafkajs consumer-group rebalance on restart.
- Live ConfigMaps (ns emr-v2) have NO `PLATFORM_*` keys yet — harmless until PR-B (nothing
  reads them), but required before the T path can be exercised on staging. Pods carry a redis
  sidecar (REDIS_HOST=localhost) so RedisJtiStore has a target.
- Verification recipe that worked (kubectl ctx lisportalprod): `kubectl get deploy -n emr-v2
  -o jsonpath=…image…readyReplicas`; dist check via `kubectl exec … ls /app/dist/modules/<mod>`;
  health via `kubectl exec … node -e "http.get('http://localhost:3000/api/v1/health')"` (pod
  has no curl/wget; `kubectl port-forward` to 3000 answered HTTP 000 in 3 s — do not rely on
  it). macOS has no `timeout` binary: `timeout 30 kubectl …` silently fails and looks like
  "cluster unreachable" (burned one round this session).
- PR-B rebased onto 10ecea0 → f0d4e31, 395 tests green, tsc/build OK. Awaiting Leo's word to
  push + open the draft PR → staging.

### [[VP-18048]] · _Lessons Learned_

### [2026-09-16] Live authenticated round-trip on staging (the gap the closeout flagged)
- Leo asked for two runnable `getEvent` packages, one that sees internal_notes and one that does not. Done on staging `https://api.vibrant-america.com/v2/portal/trans-service-st/graphql` (prod has 0 non-null internal_notes rows, so only staging can demo it).
- Demo data found in `calendar_dev_new`: 3 events carry internal_notes (13407, 13612, 13651 — all FE/VP-18049 test writes by Zhiheng Wu). Target = event **13651**, calendar **35740** (`role=patient`, `practice_id=150105`, `calendar_owner_id=999997`), active (is_canceled=f).
- Tokens minted locally (HS256, `secretOrKeyDev` from the transv2 `.env` — staging runs on the **dev** secret; `secretOrKeyProd` is rejected there with `Invalid token`).
  - clinic: `{user_id, customer_id: 999997, clinic_id: 150105, user_roles:['provider'], email_log_in_id}`
  - patient: `{patient_id: 999997, clinic_id: 150105, barcode:'2609046009', role:'patient'}` — patient_id MUST equal `v2_calendar.calendar_owner_id` and clinic_id equal `practice_id`, otherwise `getEventByEventId` fails earlier with FORBIDDEN "Patients can only access their own patient calendar" (service-level gate, before the field gate).
- RESULT (both `getEventByEventId(eventId: 13651)` and `getEvents(calendar_ids:[35740], 09-25..09-26)`): clinic token returns `internal_notes = "This is the internal notes that has been updated. test test"`, patient token returns `internal_notes: null` with identical `notes` / `event_title`. The field gate is now proven live, not only by the Apollo wire spec.
- Script kept in the session scratchpad only (contains signed tokens) — not committed.

### [[VP-18048]] · _Decisions Made_

- Internal user = any non-patient token (Leo 2026-09-02). Implemented as `canReadInternalNotes(userType) === (userType === 'clinic')`, fail-closed on undefined.
- Two columns: `v2_event.internal_notes`, `v2_event_exception.updated_internal_notes` (both nullable TEXT). Migration `prisma/manual-migrations/20260902_add_v2_event_internal_notes.sql` + `scripts/vp-18048-apply-migration.js` (per-schema, idempotent, verifies both columns after).
- Write gate `assertCanWriteInternalNotes(user, input)` at all 4 mutation entry points (createEvent, updateEvent, createEventByPatient, updateEventByPatient) + rescheduleClinicalConsult (which had NO patient check at all — pre-existing gap, noted).
- Kafka `addon_column` spreads the whole row in two services → both go through `omitInternalEventFields()` from one module so they cannot drift.
- Not touched: daily-report xlsx (internal recipients, PRD didn't ask), inbound Google/Outlook sync (writes `notes` from external description; never writes internal_notes), meeting-request → event creation (no source for internal notes).
- Worked in a worktree `~/src/LIS-transformer-v2.worktrees/VP-18048` (node_modules + .env symlinked to main checkout, existing convention). Local commits only, NOT pushed — Leo reviews first (lis-prod-change-gate final step).

### [[VP-18050]] · _Decisions Made_

- **Leo chose Approach A (2026-08-31)**: batched GraphQL query in transv2. No Jira comment for now — draft it after the work is done.
- Batch cap set to 20 (`MAX_CLAIM_STATUS_BATCH`), matching the modal's `searchResultLimit`. It is a probing limit, not a performance one: the query takes arbitrary accession ids and never checks clinic ownership, so an uncapped batch would sweep for other practices' bookings in one call.
- Extracted `CLAIM_DISCLOSURE_SELECT` + `toClaimResult()` so `isClaimable` and `claimStatuses` share one mapping. Two independent copies of the disclosure gate is exactly the drift the "sync sibling encodings" lesson warns about — the gate is a privacy control, and a batch path that quietly disagreed with the single path would be invisible.
- Result carries `accession_id` per row and preserves request order, so the FE can zip it against its rendered list without a second lookup.

### [[VP-18085]] · _Lessons Learned_

- emr-v2 deploy target for feature PRs is `staging` (no `stage_test` branch); `staging -> main`
  release PR deploys prod. Both AKS pods rolled ~20 min after merge.
- For the API order path, `patient_not_found` can mask a coresamples GetPatient decode error —
  always check `v2 getPatient failed` in the pod log before trusting the reason.
- productMap external codes are case-sensitive; lower-case codes are unrecognized, not normalized.

### [[VP-18085]] · _Lessons Learned_

### [2026-09-09 17:10] Follow-up (Leo): does pricing dbs_mapping actually have data? — YES
- How va-portal decides "same test": NO dedup. Global `isDbsVersion` toggle (At Home Test Menu);
  the other version's items are unselectable (`isItemAllowedForCurrentMenu`, FavoriteTestCard
  `isTestAllowed` via dbsMap.dbsItemId); toggling runs `getAffectedItemLists` which swaps every
  cart item serum<->DBS through dbsMap (originalItemId->dbsItemId) or discards it; order submitted
  with a single `dbs` boolean. Identity source = pricing `dbs_mapping`, never names/codes.
- Live GET `/item/price/getAllTestsAndDiscountPanels/usd` (prod via JWT_SECRET_PROD customer
  3194/clinic 125613; staging via JWT_SECRET_DEV 999997/10136): `atHomeMappings` = 20 rows on
  BOTH, byte-identical (16 test + 4 bundle). 14/15 productMap `_DBS` pairs present and matching
  (178->665, 60->586, ...). **FOOD_ADDITIVES 165->620 is NOT in dbs_mapping(is_new=true)** —
  suffix rule catches it, dbs_mapping would not (or it sits under is_new=false, not exposed).
  6 mappings have no external-code pair: test 160->612, 849->850, bundles 18008->18011,
  18009->18012, 18010->18013, 1->6 (not orderable via API codes today).
- Implication for option B: data exists and is stable; emr-v2 could fetch this endpoint (cached
  in pricing redis) to build originalItemId<->dbsItemId and key layer 2 on it instead of the
  suffix, keeping the suffix as fallback (FOOD_ADDITIVES gap). Scripts: scratchpad bestdeal.js, cmp.js.

### [[VP-18138]] · _Lessons Learned_

### [2026-09-18] Closeout audit (dream) — chain PASS through main 1d72a0b; FLAG unchanged (Done 09-11, three more deploys with zero ticket trail; real-vendor round-trip under the final code still pending)
- Merged since Done: #420/#421 (09-15, DDL applied before deploy), #422/#423 (09-16 23:26Z, delayed job, no DDL), #425/#426 (09-17 18:28Z, order-id file names, no DDL). Jenkins `continuous-integration/jenkins/branch` success on 172a7f3 / 04def1b / 8b8e625 / 1d72a0b. AKS prod deployment image = 1d72a0b tonight (pod 74688f6774-lklqk, 0 restarts, 0 error lines in 6 h).
- Live legs after each deploy: 09-16 canary through the real queue (delay 120 s exact, retry at +120 s exact, DELIVERED + peer sha256); 09-17 three naming branches DELIVERED + path-escape dropped + parent dirs untouched. `order_attachment_records` tonight = 11 rows (5 DELIVERED, 6 FETCH_ERROR — all 6 are the 09-16 pre-fix pair + canary rows, none after 09-16 23:46Z). vendor 44: deliver_order_summary_pdf 0, sftp_order_forms_path `/Prod/FollowThatPatient/Order/Forms/` (only non-NULL row).
- Post-deploy intake health: 9/9 hl7_file_input rows since 09-17 18:40Z parse_finished=1 with sample_id. No FOLLOWTHATPATIENT order since 7124 (09-16) -> the two real test orders were hand-delivered; the deployed code has still never produced a DELIVERED row for vendor 44. Decisive evidence remains the next real Prospera order (file must lead with their ORC-2 id).
- Ticket: 3 comments total, last one Zhenhe's "It is acceptable" (09-11). Nothing about the order-time redesign, the DDL, the delayed job, or the naming change. Closing comment for Leo still not drafted (flagged 09-15, again tonight).

### [[VP-18138]] · _Lessons Learned_

### [2026-09-19] Dream re-check — no change on prod; row-count correction
- `order_attachment_records` = **10 rows** (5 DELIVERED vendor 2; 5 FETCH_ERROR = the 09-16 vendor-44 pair + 3 canary rows with sample_id 1). The 09-18 audit line said "11 rows / 6 FETCH_ERROR" — that was a miscount, the documented set has always been 10; no row deleted (newest still `cmu5vjxcp…` 09-17 18:40:08Z). 0 rows in the last 24 h.
- vendor 44: `deliver_order_summary_pdf` = 0, `sftp_order_forms_path` = `/Prod/FollowThatPatient/Order/Forms/` unchanged. No FOLLOWTHATPATIENT order in the window (only 1 hl7_file_input row since 09-19 01:52Z, MDHQ, parsed). Decisive evidence (first real Prospera order through the deployed code) still pending; closing comment for Leo still undrafted.
- Prod emr-v2 pod `74688f6774-lklqk` 0 restarts, 0 error lines in 24 h; 40/40 result pushes TRANSMITTED in the window.

### [[VP-18138]] · _Decisions Made_

### [2026-09-15 11:15 PDT] Vendor answered the folder question -> order-forms path DECIDED
- Next-Health/Prospera reply (pasted by Leo): "For SFTP, somewhere under the Orders folder is fine.
  Any sub-folder structure you implement for this will work, just let us know the path you choose
  and we'll get it set up." -> the other 3 questions from the 09-11 draft (file split / no blood
  tubes / re-drop on edit / UI surfacing) are still UNANSWERED.
- Live SFTP tree re-verified 09-15 (read-only paramiko ls, vendor 44 creds from prod):
  `/Prod/FollowThatPatient/{Order/ (0 files, only archive/ with the 2 fetched ORDER_*.hl7),
  Results/ (3 hl7 + Processed/ 910)}`. No Forms/ or equivalent exists. Their "Orders folder"
  = `Order/` (singular) = `ehr_vendors.sftp_ordering_path`.
- Safety check before committing to a sub-folder of the pickup dir: `hl7-order-fetch.service.ts`
  `listFiles(serverFolder)` lists ONE level and filters `isFile && /(\.hl7|\.HL7)$/` -> sub-folders
  are never descended into, so `Order/Forms/` cannot interfere with order pickup or be archived.
  Write perm under `Order/` already proven (our fetcher created `Order/archive/` itself).
- **DECIDED (Leo 09-15): order-forms drop path = `/Prod/FollowThatPatient/Order/Forms/`**.
  Filenames proposed to vendor: `{barcode}_ordersummary.pdf` + `{barcode}_blooddraw.pdf`
  (barcode = `hl7_file_input.julien_barcode`, same identifier as the result file `{accession}.hl7`;
  verified format match, e.g. 6762 -> 2608016036 vs result 2608316087.hl7).
- Vendor creates the folder ("we'll get it set up") — do NOT mkdir it ourselves; re-verify existence
  + write access before the first drop.
- Email drafted for Leo to send (path + filenames + our folder behaviour + re-ask of the 4 open
  questions). NOT sent by agent.
- OPEN / not yet approved: implementation shape. Proposal = new nullable `ehr_vendors
  .sftp_order_forms_path` (vendor-level, mirroring `deliver_order_summary_pdf`) rather than a
  hard-coded path; needs prod DDL -> `lis-prod-change-gate` + Leo approval before any code.

### [[VP-18288]] · _Lessons Learned_

- **Transmitted-artifact reconstruction beats config archaeology.** `ehr_integrations` keeps no
  history (`updated_at` does not auto-update, notes only written by the LIS-7716 PATCH path), so
  "what was configured at send time" is unanswerable from the config tables. But
  `file_size_bytes - (CHAR_LENGTH(generated_hl7_content) - 36)` recovers the exact base64 payload
  length of every past push, and the pdf-cache endpoint still serves both styles on demand. That
  turns a "unverifiable historical state" question into an exact byte comparison.
- **Pick a neighbour when the subject is contaminated.** The cited accession was compressed and
  therefore mute. The sample pushed 47s later on the same integration was not, and answered the
  same question.
- **Compression silently erases the style signal at ~20%.** Any P2P/DEFAULT-vendor push whose source
  PDF exceeds 10MB cannot be style-identified from its transmitted size. Worth remembering before
  concluding anything from a single large record.
- LIS-7716's duplicate-LIVE-row hazard is real for this clinic (two LIVE rows, one CLASSIC) but was
  NOT the cause here - always check `result_transmission_records.integration_request_id` before
  blaming the sibling row.

### [[VP-18344]] · _Decisions Made_

- Draft PR, not mergeable until prod core-v2 >= 0903103b. emr-v2 STAGING reads PROD core-v2 for v2 calls
  (GRPC_V2_*_HOST=10.224.0.10:32100), so staging emr-v2 must follow prod core-v2, not staging core-v2.
- Wire-compat spec lives in src/proto-v2 but covers both sets (entry-file loads, samples types, Address
  layout both sides + tag-for-tag agreement, round-trip).

### [[VP-18372]] · _User Feedback_

### [2026-09-30 11:50] Follow-up: 64.124.9.100:2223 question + per-file destination comment (189923)
Leo asked whether the "vendor" jagconsulting@64.124.9.100:2223 had been deleted. Verified in prod lis_emr:
- It is NOT an ehr_vendors row and never was. It is the quarterly periodic-report drop in
  `emr_periodic_report_customers` (customer 30248, /Prod/JAGConsulting/Results, created 2025-12-11,
  updated_at untouched, row still present). Last successful use: Q2 2026 run 06-30 (110 records).
- ehr_vendors id gaps explained: 17/18/43 = VEJO deletion 2026-08-04; 20-31 = 12 ids consumed by the
  failed first pass of the 2026-01-02 emr_sftp_source migration (matches the 12 rows 32-43). No orphan
  FK residue in sftp_templates / test_name_mappings / integrations. 64.124.9.100 vendors are only
  Breathermae :2222, FollowThatPatient :2224, DocVilla :2225. Retired emr_sftp_source snapshot has no JAG.
- Datadog 90d (flex) for jagconsulting / that path: 0 hits. emr-v2 repo: only docs + scheduled-reports CSVs;
  commit 52b347e (2026-03-02) put the plaintext SFTP password in docs/SYSTEM_ARCHITECTURE_GUIDE.md (still on main).
Posted Jira comment 189923 (Leo instructed to post directly): all 29 barcodes went to both live integrations,
all TRANSMITTED, sftp_host NULL in records = vendor-level creds. P2P labftp.power2practice.net:22
lab-vibrantamerica /public/; BioInsights sftp.bioinsights.com:2022 vibrant-wellness /incoming/.
Stated that 64.124.9.100:2223 is periodic-report only and none of the 29 HL7 files went there.

### [[VP-18402]] · _Lessons Learned_

### [2026-09-28 22:40Z] Dream closeout audit — PASS (armed, not fired)
- Chain re-verified from ground truth: #435 → staging 644c344 and #436 → main b9976cb both `continuous-integration/jenkins/branch` success; prod pod now on 8c99cde (#438, superset), staging on 9fec7d0. No DDL for this ticket.
- Prod effect since deploy (lisportalprod2 read-only, 09-28 22:30Z): `ehr_integrations` moved to REJECTED since 09-25 = **0**, status_history LIVE→REJECTED since 09-25 = **0**, LIVE+ordering rows 898 (was 897). `hl7_file_input` 09-24..09-28: 31 files (MDHQ 19 / THM 11 / BIOINSIGHTS 1), all parse_finished with sample_id, `provider_not_in_clinic` never set. Only error-level pattern on emr-v2 prod in the window is a one-hour ECONNREFUSED ::1:6379 burst at the 09-25 23:xxZ deploy (216 lines, one pod, never recurred) plus the usual grpc keepalive noise.
- Still armed, not fired: the gate has rejected nothing and the success path has not run in prod. Trigger = a real provider removal through the portal; observable = first `provider_not_in_clinic` row in `hl7_file_input` or first REJECTED row with `changed_by` = a portal user via trans.

### [[VP-18402]] · _Decisions Made_

Leo, 2026-09-25, answering the Step 4 questions in order:
1. **Do not split half 2** — both halves ship in VP-18402.
2. **In-flight results: do not keep sending.** "只要 remove 就移除, 後續收到訊息就看是不是當下還是 live"
   — the existing `status='LIVE'` filter on the result-push path stands, no exception carved out.
3. **No backfill** of existing stale LIVE rows. Forward-only.
4. **Yes**, fix `:id/disconnect` to write the status-history row it was missing.
5. FE (VP-18403) is not ours.

### [[VP-18404]] · _Lessons Learned_

### [2026-09-28 22:40Z] Dream closeout audit — PASS (armed, not fired)
- #838 → main bc1b3ea (`lis-transformer-deploy-prod` success 23:35Z 09-25) and #839 → stage_test 9b0a49c (`-staging` success). All 3 prod trans pods still on bc1b3ea (started 09-26 00:13-00:15Z, 0 restarts); `EMR_V2_BASE_URL` present on both `lis-trans-config` and `-st` at 22:30Z 09-28 (merge-patched keys survived).
- Datadog `service:lis-trans*` since 09-26: **0** lines mentioning the deactivate call, its failure tag, or "not set" — i.e. no removal happened on either env, and the not-configured branch never logged (env is set). Success path still unverified end to end in prod.

### [[VP-18404]] · _Decisions Made_

- Both call sites wired, not just `deleteCustomerProfile`. `removeInvitation` ('Account Pending')
  calls the same core RPC, so it carries the same consequence; an invitee rarely holds a LIVE
  integration, in which case emr-v2 answers noop, and covering it costs one call.
- Gated on core returning 200. On a core failure the relationship still stands, and deactivating
  then would disconnect a provider who was never removed.
- Accepted that core answers 200 even for a non-member (deliberate v1 parity, see Ticket Analysis),
  so a no-op removal also fires the call. Harmless — emr-v2 answers noop.

### [[VP-18406]] · _Lessons Learned_

### [2026-09-30 22:2x-23:0xZ] #853 merged (2b1d9ea) but CI + staging deploy failed → root cause + fix PR #854
- Leo merged #853 at 22:23Z; `typecheck + unit tests` red: `src/setting/setting.controller.spec.ts` cannot load (`Cannot find module './setting.reportPrefer.service'`), 1106/1106 other tests pass; the staging deploy workflow gates on that job → buildImage/deploy skipped, staging still on f48bc26.
- Root cause (verified with `git diff --name-status f48bc26 2b1d9ea`): #853's conflict-fix merge DELETED `setting.reportPrefer.service.ts` + `dtos/reportPrefer.dto.ts` and stripped the endpoints from `setting.controller.ts`/`setting.module.ts` (−298 lines). Mechanism: at 20:55Z `ruichennrobot` re-pointed `stage_test` at main's head f48bc26 (old stage_test bacfeee is NOT an ancestor of f48bc26) and closed #853. Our branch still carried the old stage_test lineage incl. VP-18022 #731 (Michael, "Retire the Bespoke Report Builder endpoints", merged to stage_test 09-09; #730 → main still open). Merging the reset stage_test into it made git keep the retirement's deletions (3-way base predates the retirement) — silently, no conflict on those files — while main's `setting.controller.spec.ts` still imports the service.
- My mis-attribution to correct: earlier I called this "pre-existing on origin/stage_test" — true only because origin/stage_test already WAS 2b1d9ea (my merge) when I tested; f48bc26 was green.
- Fix: PR #854 → stage_test (`fix/leo/stage-test-restore-report-prefer`, head 3a2c23a) restores the 4 files from main; afterwards `git diff origin/main` on stage_test = exactly the VP-18406 4 files. 3 suites / 49 pass, pre-push PASS. VP-18022's staging state is Michael's call (noted in the PR body).
- Lessons: (1) `stage_test` gets re-pointed at main by ruichennrobot (sync-by-reset, closes open stage_test PRs) — after such a reset, a twin branch cut from the OLD stage_test must be rebuilt from the new base (cherry-pick), never merged, or old-lineage deletions come back. (2) Check `git merge-base --is-ancestor <old base> origin/stage_test` before choosing merge vs cherry-pick. (3) `git diff --name-status <base-before> <merge-result>` after any conflict merge, not just the files I resolved by hand.

### [[VP-18406]] · _Lessons Learned_

### [2026-09-30 22:32-22:55Z] Deployed + verified live on prod
- #852 merged 22:32:13Z (5889d59) → prod run 36786146685 all jobs success, `lis-trans-deployment` 3/3 on 5889d59 (RS 774888dbf8) by 22:47Z. #854 merged 22:32:00Z (4f44d80) → staging run 36786120119 success, st pod on 4f44d80. 0 `"level":"error"` on all pods; `/trans/*` 312 prod + 5 staging responses since 22:38Z all 2xx.
- Response logs for findPatient carry no body (message empty), so no log-based proof. Instead: `fp-probe.js` from prod pod 774888dbf8-2wl85 with the pod's own internal `token` (JWT customer 9708 / clinic 10136, role ss) → `POST /trans/findPatient` (required DTO fields: page, perPage, sorting_field_input, sorting_order_input, kit_status[], issue[], report_status[], order_type[], start_date, end_date, search_patient_type, search_patient_field, flagged; `resolveIdsForHttpOptional` takes customer_id/clinic_id from the body when absent from the JWT). Result 200, 35 KB, 22 order rows all with consultationEligible=true / reason=null. No PHI printed (tally only).
- Jira comment posted (deployed + live check + stage_test side note); ticket left Dev In Progress pending VP-18407 contract confirmation + QH-7277. BE work complete.

### [[VP-18406]] · _Lessons Learned_

### [2026-10-02] Closed: Dev In Progress -> Done (transition 15)
- Leo: BE complete means close it; no need to wait for VP-18407 contract confirmation or QH-7277. Transition 15 went through with no required-field validator (Task type; the Root Cause validator seen on VP-18243 applies to Bug).
- Closing comment posted: deployed/verified summary + follow-ups delegated to VP-18407 (FE contract), QH-7277 (QA), and a core change if product wants the withdrawn-report / cancellation-timestamp edge cases enforced. No reply from Xiaoye or product on the two data gaps as of closing.

### [[VP-18406]] · _Decisions Made_

- 2026-09-30 Leo: 「做」. Approach = per-order computation inside `cleanOrderlitenew` (zero upstream calls), fields `consultationEligible` / `consultationIneligibleReason`, proposed reasons OUTSIDE_WINDOW / CANCELED_NO_RELEASED_REPORT / NO_ELIGIBLE_DATE (FE confirmation requested on the ticket). Jira comment 189934 posted with findings + asks (Xiaoye/VP-18407 contract, QH-7277 test orders); transition 3 → Dev In Progress. Implementation delegated to a subagent: branches feature/leo/VP-18406 (main) and -stage, pure module `src/trans/consult-eligibility.ts` + unit tests per branch of the rule + a cleanOrderlitenew stamping test; it must report how withdrawn/invalidated and canceled are detected in the payload.

### [[VP-18481]] · _User Feedback_

### [2026-10-13 16:40] Leo: "以後做完需要我 merge 都要給我 PR"
- Rule: whenever a deliverable ends in a PR that Leo must merge (main / release / factory lesson PRs), the report must carry the PR URL itself, not just the number. Triggered because the closing report named factory PR #95 without its link.

### [[VP-18593]] · _Lessons Learned_

- BSD `seq` on macOS formats with %g: ids >= 1e6 become "2.5983e+06" and collapse per 10. Use `seq -f '%.0f'`; validate /^\d+$/ in any harness that forwards ids to a string RPC field. Caught by the shipping team via a Datadog trace, not by us (2026-09-30).

### [[VP-18782]] · _Lessons Learned_

### [2026-10-13 00:05Z] Both PRs merged; staging VERIFIED; prod waiting on a Jenkins scan
- #211 -> dev 23:37Z (9a556cf), dev build success 23:43Z, staging pod on `lis-sample-staging:9a556cff` 23:42Z. #210 -> master 23:46:35Z (19fbb0f) — master head has NO Jenkins status yet (no webhook): prod still on 3a44ca9c until someone runs Scan Repository Now.
- Staging probe (curl to /v1/lis/samples/staging with a fake HS256 Bearer, Cookie, JSON body with an email): pod log `req` = {id, method, url, remoteAddress, headers{host, content-type, content-length, user-agent, x-request-id, x-forwarded-for}} only; zero hits for the token / cookie / email / "authorization" in 6 min of log; caller_attribution line still carries claims {sub, internal_user_name, role}. Note: LoggerMiddleware.normalizeRequestId replaces a non-UUID x-request-id with a fresh UUID, so grep by route, not by the probe id.
- NEXT: after the master scan + prod rollout (image 19fbb0f5), Datadog `service:lis-sample-deployment @req.headers.authorization:*` must show 0 lines after the rollout timestamp and `@event:caller_attribution` still has `@claims.*`; then Jira Done.

### [[VP-18796]] · _Lessons Learned_

### [2026-10-13 00:55Z] Step 2 - analysis (Explore recon + live state)
- **Plan conflict**: trans v1 `protos/trans-service-protos/trans_service.proto:7-19` (VP-18612 / VP-18613, 2026-10-02): "trans is meant to be a frontend BFF only; this gRPC service is being retired. Do not add methods or new backend callers." Epic VP-18612 (Xiaoye, Dev In Progress): GetSampleInfo callers -> trans HTTP; GetPatientPageStatus -> core v2 (VP-18710, Zhibin, 10/16); GetReporteStatus -> report service (VP-18708 LIS-Shipping Siyun, 10/23); gRPC server shutdown VP-18711 11/6. => the Phase A "new TransService RPC" shape is dead for this ticket; same applies to VP-18795's `TransService.GetSampleStatus` for trans v2 and to the results-retrieval RPC.
- **What LIS-Shipping actually consumes** (origin/master): operation-settings -> only `data.contains_hormones` (`orders.hormones.service.ts:2900-2930` retrieveSampleOperationSettings, called per sample id by retrieveSampleHormQnrStatus for HTTP `GET /orders/samples/horm-qnr/status`); `/tests` -> only `sample_tests[].test_id` + `test_status==='approved'` vs HORMONE_RELATED_LAB_TEST_IDS (`orders.service.ts:15494-15542` checkIfHormoneQnrEditable, errors swallowed -> editable); pns-jwt -> only `data.pns_jwt` (`orders.service.ts:18194-18218` in sendPnsNyWaiverForm, throws if missing).
- **Where LIS-Sample gets them**: contains_hormones = order-service `orderTest/getQuestionnaireRequiredMap`.has_hormone_questionnaire (utils.service.ts:766-819, 5-min Redis cache, 3 s timeout, `|| false`); test_status = results-grpc `TestResultInfoGrpcService.getTestsResultsRelatedData` (tests.service.ts:359-410) merged over Core ListSampleTests; pns_jwt = HS256 sign of {patient_id, customer_id, clinic_id, role patient, internal_user_role admin, exp +6h} with AUTH_JWT_SECRET (patients.service.ts:2085-2124), ids from Core v2 BatchGetSamples. getSampleId = shipping gRPC GetSampleId (Shipping -> LIS-Sample -> Shipping loop).
- **Shipping already has**: `retrieveQnrRequiredMap()` calling the same order-service route (`orders.service.ts:17582-17618`); `LIS_TEST_RESULT_GRPC` client to the same results host (`utils.module.ts:195-210`, only tnp.proto today); injected `AUTH_JWT_SECRET` (auth.module.ts:62); Core v2 BatchGetSamples client; `LIS_TRANS_GRPC` client (trans_service.proto copy is stale).
- **Live state**: Shipping prod `LIS_SAMPLE_HTTP_URL=https://api.vibrant-wellness.com/v1/lis/samples/` (public ingress), `LIS_TRANS_GRPC_URL=lis-trans-service-rpc:3192`, `LIS_TEST_RESULT_GRPC_URL=lis-test-connect-grpc-service.results:6889` (= LIS-Sample's). AUTH_JWT_SECRET: shipping-secret-prod == sample-secret-prod (sha 6ee45d03), staging == dev (710816ad) -> locally minted pns_jwt is byte-equivalent. Shipping prod 3 replicas on d6132581, staging 5d145259.
- **Delivery constraint**: agent cannot push to LIS-Shipping (push=false, no forks) -> `git format-patch` hand-off to Leo; LIS-Sample side needs no change until the family is deleted.

### [[VP-9299]] · _Lessons Learned_

1. **Gate 斷言要找 writer，不要只找 reader。** 看到 `if (await checkX(...))` 就相信有去重是錯的；
   必須 grep 出寫入那把 key 的 call site，並確認它沒被註解掉。本次 `cheackRedisNolock` 就是死碼。
2. **`.env` 不是線上值。** 任何 `process.env.X` 的行為推論，要對 deployed ConfigMap/Secret 查證。
   本次 `envm` 在 repo 是 `stprod`、在 prod 是 `prod`，直接翻轉了 Kafka sessionTimeout 的分支。
3. **舊 STM 的 file:line 可信度 >> 其因果結論。** 兩個月前的分析結構全對、結論全錯。
   重用舊分析時只繼承索引，結論一律重推。
4. **子 agent 的結論也是假設。** 正反兩方都寫錯了同一條（Kafka 重投會重寄信），
   我第一次轉述給 Leo 時原樣傳遞。轉述前要自己驗。
5. **辯論的產出不是「選 A 或 B」，是「你沒想到要查的地方」。** 本次最大價值是反方逼出
   ConfigMap 查證，進而發現 45s sessionTimeout；那條讓原方案（採用 V2 helper 的 10x5s retry）
   從「較好」變成「有風險」，最小改動反而勝出。

---

## Scope / requirement / PM communication <a id='scope-comm'></a>

### [[INCIDENT-20260518]] · _User Feedback_

### [2026-05-18] Leo 觀察到 sample 2552289 manual retry 就 OK
→ 證實上游錯誤 transient，emr-v2 應該 retry。改 retry 條件擴大到 UNAVAILABLE/UNKNOWN/INTERNAL（43dea1b）。

### [[INCIDENT-20260529]] · _Lessons Learned_

### [2026-05-29] 寫進 LTM 的
1. **SFTP 連線 fail 有兩種：(a) server down（TCP 不通）；(b) auth rejected（TCP 通、SSH handshake server close）** — `Unexpected end event` 是 (b)、特徵是 ssh2-sftp-client 印 `getConnection: Unexpected end event`、純 ssh 印 `Permission denied (publickey,password)`。診斷順序：先 `nc -zv host port` 區分、再用 `ssh -p ... -o PreferredAuthentications=password` 看 server 拒哪一階段 → 寫 patterns.md
2. **JOIN with NULL 欄位的 UPDATE scope 必反向 audit**：UPDATE-WHERE-JOIN 後跑「broader criterion 找漏網」query，例如 customer_id 配對但 clinic_id NULL/不同 → SQL 標準 `NULL=NULL = false` 會 silently 漏掉。VP-16175 / 本次 508387 都是同類 → 寫 patterns.md
3. **`integration_type` 跟 `ordering_enabled` 在 prod 容易漂移**：826 個 LIVE row 是 RESULT_ONLY+1（合約 RESULT_ONLY 但實際下單）、80 個 RESULT_ONLY+0 但在 order_clients。**v1 truth（order_clients）才是 ordering 與否的權威**，ei 兩欄常常過時。定期 sync 一次（join cust_id+clinic_id OR NPI）→ 寫 emr-integration.md
4. **Cat 1: 225 oc customer 沒對應 ei** — v1 → v2 migration 還沒完成的尾巴。需要 INSERT 新 ei row（不能 UPDATE 解決）。default 欄位（status / go_live_date / clinic_name / contact / sftp_*）要 PM 決定，不能自動推。

### [[INCIDENT-20260604-mdhq-stale-connections]] · _User Feedback_

### [2026-06-04 ~17:00 UTC] Leo's directives
- "我只要一切的 outcome 都一樣" — locks scope to internal lifecycle only. No cron grouping (Approach A) since that changes folder iteration timing/order.
- "再也不要發生這種 connection left open" — fix must root out leaks, not just reduce frequency.

### [[INCIDENT-2604156666]] · _Lessons Learned_

1. **v1 (`lis` @ `:30276` Java) 跟 v2 (`coresamples_service` @ `:32100` Go) 是平行 service，不是 upgrade 關係** — git blame c0852d0 + 看兩個 repo 的 commit 歷史就知道。誤當 upgrade 替換是這次 incident 根因。
2. **Go gRPC server marshalling 跟 Java/Node 不同**：Go `time.Time{}` zero → `"0001-01-01T00:00:00Z"`、Go `int64(0)` → `"0"`、Go `string("")` → `""`。Java/Node 對 missing field 通常回 null/undefined。跨 language gRPC primary swap 必須驗證 marshalling 邊界。
3. **替換 RPC primary 前必跑 end-to-end diff script** — 已寫進 user feedback memory `feedback_end_to_end_equivalence.md`
4. **outbound HL7 缺 schema validator**：date < 1900 / year=0001 應該在 SFTP push 前 reject。建議：generation pipeline 加 sanity check（不在本 hotfix scope）。
5. **多源 collection_time 問題**：emr_sample DB (`2026-04-16 08:00`) 跟 v1 gRPC (`2026-05-06 18:25`) 不一致 — emr-v2 內部 emr_sample 寫入 vs LIS coreSamples 即時返回 不同 source-of-truth。getValidCollectionTime 用 earliest-approval fallback 蓋過去 — 不算錯但讓 OBR-7 偏離 vendor 期望值（~1 天）。Follow-up 另開。
6. **service.spec.ts 不可信賴**：HEAD baseline 6/6 fail 累積多層 stale（DI / mock shape / payload casing / business behavior）— 沒人跑就沒人修。應該 CI gate 上把該檔 spec 列必過。
7. **host migration vs service migration 區辨**：
   - **Host migration**（VP-16685 cloud mirror）：同 port、同 package、同 backend、只換 IP — 安全。
   - **Service migration**（c0852d0 想做的）：換 port / 換 package / 換 backend language — 是兩個獨立 service，當全新 integration 處理，跑完整 contract 測試。

### [[LBS-1799]] · _Lessons Learned_

### [2026-09-22 10:44] Closeout — Jira comment posted + Done (Leo: "comment 到 ticket 裡面然後 done")
- Comment id **188698** posted on LBS-1799 via the claude.ai Atlassian connector (the `vibrant` MCP cannot see the LBS project at all). Covers every AC: override not needed / FE-only rule with file:line, the two-call supported path, scope + unchanged service date, Gate 7 verification, clinical-team availability source, both confirmation emails, the audit sentence, and a SIIR-312 recommendation (measure the window from specimen receipt or report completion, not `order_service_time`).
- Transitioned **Open -> Done** (transition id 61 "Mark as done", status 10228).
- **Gotcha worth keeping:** in the LBS project (Jira Service Management) the author has NO permission to edit their own comment — `addCommentToJiraIssue` with `commentId` returns "you do not have the permission to edit this comment". Get the markup right on the FIRST post. Also: pass `contentFormat: "markdown"` and use real markdown (`##`, backticks, `>`); Jira-wiki markers (`h.`, `{{...}}`, `{quote}`) are NOT converted and render literally.

### [[SANDBOX-SEED-W2W-20261005]] · _User Feedback_

### [2026-10-08 12:20 PT] Leo's note to Yekai — VERBATIM (Leo: 「記我的口吻」)
```
@Yekai Liu 以後在 staging 建立假資料的時候，core 的 order_info.order_report_status要一起設，不然 GET /orders 的 list 看不到：有 preliminary 設 report_pending，final 出來設 report_ready。M06/M07 這兩筆我這次已經補好
```
Diff vs my draft (same structure kept: rule -> reason -> values -> what is already done):
- 「之後在 staging 造報告資料」 -> 「以後在 staging 建立假資料的時候」: plainer verb (建立 not 造), and the
  rule is stated for ALL fake data, not only report data — he generalises the rule, I scoped it.
- 「我已經補好了，不用動」 -> 「我這次已經補好」: drops the instruction to the other person (不用動) and
  adds 這次 — states what he did, does not direct Yekai's next move. Same rule as the 10-07 partner
  reply: say our facts, do not schedule the other side's work.
- Keeps the English field/value names inline, colon before the two values, no greeting, no bold.

### [[VP-16514]] · _User Feedback_

### [2026-06-04] 分析格式規則（Leo 明確要求，套用所有未來 ticket）
未來分析一定要包含、且用看得懂的話寫：(1) 這張 ticket 的**目的**（PM 想達成的效果）(2) **改之前**長什麼樣子 (3) **改之後為什麼**能達到這效果 (4) 要**透過改什麼**完成需求。只寫技術細節（endpoint/欄位）Leo 看不懂。已存 LTM [[feedback_analysis_format]]。

### [[VP-17344]] · _User Feedback_

### [2026-07-08 15:00] Cursor-bot review fixes (commit 0ad35ca)
- Bot HIGH (valid, my miss): listener's own ensureTransmissionRecord findFirst lacked `push_scope_key: null` — I scoped generation service + processor but missed the listener's whole-order lookup; a newer partial record would be reused/reset by report_finished. Fixed + regression test.
- Bot MEDIUM (valid): placeholder record created before enqueue → enqueue failure (or lost job) shields the scope forever for REPORT scopes. Fixed: delete placeholder on enqueue failure; REPORT dedup now = delivered(TRANSMITTED) blocks forever, undelivered blocks only 24h (later ready/viewed event retries). 3 new tests; spec now 8/8.
- Working-dir gotcha: main repo checkout had been switched to feature/leo/VP-17363 by another session — fixes done in a git worktree `.claude/worktrees/vp-17344` (repo convention; `cp -Rc node_modules` APFS-clone + own `prisma generate` per worktree, never share the generated client across branches).

### [[VP-17344]] · _Decisions Made_

### [2026-07-08 11:50] Leo confirmed scope (Step 4)
- "全部都先只有 final result ready 才 push, 我會手動調架構, 只要有功能, 現在要讓 end user 感受不到差異" → build both partial levels, ship with everything at WHOLE_ORDER default; Leo flips DB values manually later; zero behavior change on deploy is the hard requirement.
- Design defaults locked: partial pushes force add_report='0'; final whole-order push retained for partial-level integrations; redraw stays whole-order; REPORT scope never re-pushes (viewed events no-op forever), SAMPLE_TYPE scope re-pushes after 24h (redraw→re-finish).

### [[VP-17499]] · _Decisions Made_

- [2026-07-27] Leo: 做，拆 2-3 commits。
- Two-phase index swap (expand/contract): part A add column+composite (legacy global unique KEPT — deployed old code derives its idempotency P2002 from it; dropping early = zero duplicate protection until promotion). Part B (drop legacy) only after code live on BOTH envs.
- Derive-scope tokens (VP-17450, ctx.customerId null): namespace owner = provider's customer, resolved read-only BEFORE the intake insert (mirrors enrich()'s fetchById/fetchByNpi branching; fetchByIdScopeOnly path not needed — it only applies to token-customer which implies ctx.customerId present).
- Interim collision (P2002 but no row in caller's namespace) -> 422 rejected placer_id_conflict; never return the foreign row. Dead code after part B.
- Later status writes address the row by primary id (rowId), not placer string — cannot touch a foreign row.

### [[VP-17591]] · _Decisions Made_

**Scope discipline**: only `parse()` (HL7) switched. `assembleWithNyRouting`
serves the **API** intake path where the caller sends only `patient_id` and never
an address — inbound-only there would reject every GZ order; that path is guarded
by eligibility-check, which validates address itself. Verified the two paths share
no call site.

### [[VP-17628]] · _Decisions Made_

### [2026-08-06] Leo Q: do pure-clinic tokens (no customer) exist? How many clinics lack a default?
- Partner token shape VERIFIED live (sandbox token exchange, QA client vac_GHkfxeziakflJhxmLJIzOA + decode): RS256 client-credentials token DOES carry both `customer_id: 50661` and `clinic_id: 153884`, role=CUSTOMER (OAuth service embeds the client's bound ProviderID/PracticeID as claims). So current API partner tokens are fully scoped — NOT the scope-less derive-scope kind; a "pure clinic token" (clinic without customer) does not exist on this path today. Non-privileged tokens missing either id are 400'd by controller; privileged (admin/service/INTERNAL) go derive-scope and keep requiring orderingProviderId under my design.
- defaultProvider coverage (ClickHouse 192.168.62.85 lis_core_v7_replica, Prisma m2m: setting + _clinictosetting join, A=clinic_id B=setting_id; NB _ab_cdc_deleted_at is EMPTY STRING not NULL): active clinics 52,615 → usable value 19,551 (37%); row-with-EMPTY-value 19,399 (37%); no row 13,665 (26%). **63% of active clinics have NO usable defaultProvider — unset is the majority case.**
- Beta partner clinics: only MyResilienceCode 153883 → 16921 set; GetHealthy 153881 / Junction 153880 / InfinityNeuroMotor 153882 / QA 153884 all NULL/empty. VP-17472 repro clinic 125613 → 3194 (= its token customer).
- Design consequences confirmed: (a) token-customer fallback (Leo's decision) is the DOMINANT path in practice and always has a value to fall back to; (b) empty-string setting_value MUST be treated as unset (19.4k clinics have empty rows) — matches transformer read parity.

### [[VP-17748]] · _Decisions Made_

- First pass applied only the two hunks that exist in emr's copy and left
  `order_shipping_issue_status` out; Leo chose the fuller sync, so it was added at v1's
  number 31 (emr's copy never carried it at 28 at all -- it stopped at
  `order_major_status = 27`). The vendored proto is now byte-equivalent in field numbering
  to #921's head, which is what Phase 4's identical-protos requirement wants.
- Leo asked for a dedicated ticket rather than working under VP-17511 (Fan Zhou's).
  VP-17748 created + assigned to Leo, linked `Relates` to VP-17511. Branch renamed
  `bugfix/leo/VP-17511-proto-field-sync` -> `bugfix/leo/VP-17748` before the first commit.
- Kept the PR's explanatory comments in the vendored copy so the next reader knows why 6 is
  free and not `reserved`.

### [[VP-17827]] · _Lessons Learned_

**Vendor confirmation (gate 2 for FOLLOWTHATPATIENT, in writing, Tom Porter 10-08).** MSH-6 and ORC-17 always carry
the Vibrant Practice ID of the location the order is placed from, for every location; value follows the location, not
the provider; ORC-12 is the provider ID set up for that provider at that practice. New from Tom: "as of our next
release, an order without a valid location is refused before it is sent" -> for this vendor the no-practice-ID case
(PM open question 1) does not arise. Tom then asked three things: (a) did our intake choose the practice from the
provider ID rather than ORC-17; (b) from what date will billing use ORC-17; (c) will the trial orders be re-billed.

### [[VP-17827]] · _Lessons Learned_

**Proposed design (waiting for Leo).**
1. Per-vendor practice-id field map, code default `{ FOLLOWTHATPATIENT: 'ORC.17' }`, env override
   `ORDER_PRACTICE_ID_FIELD_MAP` (JSON). Vendors not in the map = no practice id = today's behaviour (AC backward
   compat; 5 of 6 vendors send nothing usable per 08-21).
2. `parser.service.ts` extracts the field for the vendor; `fetchById/fetchByNpi(id, practiceId?)` ->
   `resolveOrderingIntegration(customerIds, practiceId?)` adds `clinic_id = practiceId` to the WHERE when given.
   Match -> that row. This alone fixes all 5 observed cases (ORC-17 was always one of 43262's 4 clinics).
3. Practice id given, provider has LIVE rows but none at that practice -> reject, retryable, new tag
   `practice_not_found=<provider>/<practice>` on last_error + customer_not_found column (same retry/rescan path as
   customer_not_found, VP-17120), so adding the provider at that practice re-places the order with retry_num. This
   is Xiaoye's PM case 2; engineering default = reject (booking to another practice IS the bug), PM may override to
   accept-and-flag later via quarantine.
4. Practice id field present but empty/non-numeric -> treat as absent + warn log + counter (vendor says their next
   release refuses such orders anyway).
5. Log `practice_id` + match mode on the order processing log line; no schema change.
Tests: customer-detail-fetcher.service.spec (practice filter, winner among rows at that practice, no-row ->
null-with-reason), parser.service.spec (FTP ORC-17 8003/36290 -> clinic; unknown practice -> practice_not_found;
vendor not in map -> unchanged; blank -> unchanged). Live: staging replay of the archived FTP files with staging
ehr_integrations seeded for 43262 at 2930/8003/36290; prod verify = first FTP order after deploy, core sample
clinic_id == ORC-17.
Out of code scope: re-billing/moving the 5 placed samples (ops, Keith); 7266 (catalog); other vendors (send
nothing to key on).

### [[VP-17827]] · _Lessons Learned_

Worktree `~/src/lis-backend-emr-v2.worktrees/vp17827` (branch `feature/leo/VP-17827` off origin/main c15bb82;
`npm ci` + `prisma generate` done there). 9 files, +699/-12. Not committed, not pushed (prod-change-gate: stop for
review before commit/push).
- NEW `services/practice-id-field.ts`: `DEFAULT_PRACTICE_ID_FIELD_MAP = { FOLLOWTHATPATIENT: 'ORC.17' }`, env
  `ORDER_PRACTICE_ID_FIELD_MAP` (JSON, merged over defaults, bad JSON warns once + defaults), `practiceIdFieldFor(emrName)`,
  `extractPracticeId(segments, 'SEG.n')` (MSH.n = fields[n-2], others fields[n-1]; first ^ component; positive int only).
- `customer-detail-fetcher.service.ts`: `fetchById/fetchByNpi(id, practiceId?)` overloads; `resolveOrderingIntegration`
  reads candidates as before, then filters `clinic_id === practiceId`; empty-after-filter with non-empty candidates ->
  `PracticeMismatch { practice_mismatch, practice_id, customer_ids, clinic_ids }`; `isPracticeMismatch()`.
  `fetchByIdScopeOnly` guarded (no behaviour change).
- `parser.service.ts`: after ORC-12.1, `practiceIdFieldFor(orderInfo.emrName)` -> extract -> pass to fetcher; mismatch ->
  `{ result: { practice_not_found: '<ORC-12.1 as sent>@<practice>' } }` before the PH-917 gate; unusable value -> warn +
  provider-only; success with practice -> log line `[practice-id] vendor=.. provider=.. practice=.. -> customer .. clinic ..`.
- `parse-models.dto.ts`: `practice_not_found?: string`.
- `hl7-order.processor.ts`: new branch after customer_not_found: `markFailure(id, 'practice_not_found=<tag>',
  { customer_not_found: tag }, 'practice_not_found')` -> retryable, status 'practice-not-found'.
- Specs: `practice-id-field.spec.ts` (map/env/extract, 12 cases), fetcher spec +7 (Next Health 4-row fixture: no practice ->
  2930; practice 36290 -> 36290; rank within practice; mismatch shape; no rows -> null; NPI across customer ids;
  scope-only untouched), parser spec +6 (ORC-17 passed; practice_not_found short-circuit + gate not consulted; empty /
  non-numeric / unconfigured vendor -> undefined practice; NPI path), processor wiring spec (retryable write, alert on
  exhaustion, branch ordering).
- Results: `jest src/modules/hl7-order-processing` 54 suites / 859 passed; `tsc --noEmit` clean; `nest build` ok; no CJK.
- Gate 4: `ORDER_PRACTICE_ID_FIELD_MAP: '{"FOLLOWTHATPATIENT":"ORC.17"}'` added to BOTH local ConfigMap copies
  (`~/src/lis-backend-emr-v2/lis-emr-v2-config.yaml` line 324, `-prod.yaml` line 318, gitignored). Value equals the code
  default, so the deploy works even if the ConfigMap is not synced; the env exists so a vendor can be added without a release.
- Gate 1 baseline + Leo's instruction recorded in the 18:10 section above. 7266 excluded (catalog miss).
Next: Leo review -> commit `[VP-17827] ...` -> push -> PR to `stage_test` -> staging verify by replaying the archived FTP
files (needs staging ehr_integrations rows for 43262 at 2930/8003/36290) -> Leo merges to main -> prod verify on first
FTP order (core sample.clinic_id == ORC-17).

### [[VP-17827]] · _Decisions Made_

- 2026-08-24: analysis only, no code. Reported to Leo at WORK-LOOP Step 4.
- 2026-08-24, Leo instruction "先comment 然後改成dev block" — executed on Jira:
  - Comment 185290 posted (English): blocker details in the two-part shape the VP project's
    Jira automation asks for (What's blocking / What is needed to unblock), plus the three
    findings that change the story's scope (5 of 6 vendors send no practice field; MSH-4 is
    usually the customer account number so practice must be a layered check not a replacement;
    FOLLOWTHATPATIENT already sends it in MSH-6 + ORC-17 and should be split out).
  - Status Dev To Do -> **Dev Blocked**. NOTE: the workflow has no direct Dev To Do -> Dev
    Blocked edge; the only transitions out of Dev To Do are Inactive / Done / Dev in progress.
    Reaching Dev Blocked required transitioning through **Dev In Progress** (transition id 3),
    then Dev blocked (transition id 4). The issue history therefore shows a one-step pass
    through Dev In Progress. Reusable: from Dev To Do, Dev Blocked is two hops.
- Standing rule note: instance CLAUDE.md says Jira comments are drafted, not sent. Leo's
  instruction this turn overrode that for this comment.

### [[VP-18034]] · _User Feedback_

Tone rules extracted (Leo: "請記得我的 tone"):
- One breath, 2–3 sentences, no headings, no numbered list, no "還缺兩樣" framing.
- Lead with the concrete missing inputs as a bare list of field names (what he needs handed to him), not with the status of his own work.
- State his own tickets as DONE ("都已經完成了"), scoped precisely ("只缺連到實際資料的部分") — never "還沒辦法 Done".
- Close with the blunt consequence ("現在還是完全測試不了的階段"), no next-step promise, no "兩樣到位後我會…".
- Tags both PMs (Chris Wu = spec author, Xiaoye Li), not the engineers who owe the inputs; does NOT name Rui / Fangyuan or their tickets in the ask.
- Mixed zh/en: field names and ticket ids in English inline, everything else Chinese; no bold, no code formatting.
→ leo-working-rules.md candidate: "PM comment tone" (dream).

### [[VP-18034]] · _Decisions Made_

- #410 merged → staging d67f029 (22:20:42Z) and #411 staging → main 10ecea0 (22:20:59Z);
  PR-A head 77ca209 is in main. Waiting for the Jenkins AKS roll (~20 min after merge per
  VP-18085) before any live check; PR-A has no runtime footprint, so the live check is
  "pods on the new image and healthy", nothing more, until PR-B lands.
- **Leo rule (2026-09-10): never comment on other people's tickets, not even as a draft for
  him to paste. Leo only comments on HIS OWN tickets and tags the PM there.** The VP-18089 /
  VP-18031 drafts are dropped; cross-team asks go through Leo's own ticket (VP-18034 / VP-18032)
  tagging Xiaoye, or Leo raises them in person. → leo-working-rules.md candidate for dream.

### [[VP-18034]] · _Decisions Made_

- Rui's reply to Leo: 「AI说这个ticket我不需要在OAuth动任何东西」. He closed VP-18031 Done on
  09-24 on the strength of that — the AI answered "does OAuth need changes" (correct: no, the
  spec says the platform record is not an OAuth client), nobody answered "where does the record
  live". Net: no platform record, no key store, anywhere.
- Consequence: emr-v2's env-backed EnvPlatformKeyDirectory (PLATFORM_PUBLIC_KEYS) is the ONLY
  registry that exists. Recommendation to Leo: adopt it as the production mechanism (meeting
  said "at most one or two platforms, manual"), do not reopen VP-18031. Inputs then come
  straight from the platforms (RS256 public key PEM + kid) and from charging (platform account
  id); platformId = charging account id to keep one number. No emr-v2 code change.
- Drafted a PM comment in Leo's tone for VP-18034 (not posted).

### [[VP-18048]] · _User Feedback_

### [2026-09-03] Migration applied + PRs opened (Leo: "開PR + 跑 migration")
- Schemas enumerated first: calendar_dev, calendar_dev_new, calendar_prod (calendar_dev empty/reserved, skipped). Pre-check: `internal_notes` / `updated_internal_notes` absent in both targets; `v2_event` rows 185 (dev_new) / 7857 (prod), `v2_event_exception` 0 / 0.
- `scripts/vp-18048-apply-migration.js` run against calendar_dev_new then calendar_prod: 2 DO blocks each, script's own check OK. Independent psql readback (different client, `information_schema.columns`): both columns `text` nullable in both schemas. Row counts unchanged after; all values NULL. Running prod service (old code) unaffected — Prisma selects only columns it knows.
- PR #608 → main, PR #609 → stage_test, both head `d8d9078`. No conflicts vs origin/main `748a872` or origin/stage_test `267d301`; none of the 6 new main commits touch calendar files. One head per PR — do not push more commits to this branch.
- Next: Leo merges (stage_test first per convention). Deploy is safe now that the column exists. Then: FE handoff (VP-18049), PM confirmations (role model, 2000 cap, PH-822 stop-gap) via drafts/VP-18048-open-questions-draft.md.

### [[VP-18050]] · _Lessons Learned_

- When a ticket is one half of a BE/FE split, read the other half before deciding the work is already done. The acceptance criteria of one half routinely omit the requirement that makes the other half possible.
- A PM's acceptance criterion that names *where* data should appear ("in the search response") is a statement about the user-visible surface, not about the service that serves it. Verify which service actually backs that call before designing to the sentence.
- A test that asserts "request is rejected" must confirm it was rejected by the layer under test. Auth stacks reject early and for other reasons, and the assertion looks the same either way.
- Adding a batched form of an endpoint whose response is access-gated is a security review, not a convenience refactor: the gate has to be re-applied per row, and the batch size becomes an exposure limit.

### [[VP-18055]] · _Decisions Made_

### [2026-09-01 19:10Z] Preventive PR #392 + Jira comment posted (Leo approved both)
- PR #392 (draft, base staging, head bugfix/leo/VP-18055 @ single commit): new ResultScopeDropReporterService in alerting module (VP-17544 contract clone — never throws, no-DSN no-op, PHI-free, stable message for Sentry grouping) + listener probe on the whole-order empty-resolution path: LIVE result-enabled rows on event clinic with customer_id notIn (event customer, '-1'), pod-scoped by PIPELINE_LOCATION so exactly one pod alerts. Detection at whole-order only (it is the authoritative final push for every integration, and has full event context) — partial paths deliberately not probed.
- Tests: reporter spec (full contract) + 5 new listener tests (near-miss report + probe where-shape, no-integration silence, no-clinic skip, probe-failure resilience, no-probe-on-success); updated VP-17312 pod-scope test (empty path now 3 queries). Touched suites green; parser.service.spec 3/28 failures verified identical on main (pre-existing, NY-variant fixtures, unrelated).
- Jira comment posted (id 186259) — full triage + executed fix + PR link. One-PR-one-head applies from here: no more commits to this branch.
- Still open: follow-up ticket for practice-wide option in self-service integration flow (product decision).

### [[VP-18085]] · _Lessons Learned_

### [2026-09-09 16:40] Round 2 (Leo): portal parity via pricing menu snapshot — option 3 — CODE DONE, awaiting review
- Leo's direction: stop inferring twins from the `_DBS` suffix; use pricing data and match the
  portal exactly ("不能選到兩邊"). Chose option 3 = emr-v2 reads getAllTestsAndDiscountPanels
  (no pricing repo change, no second DB). Scope assumption (Leo did not answer explicitly):
  mixed-menu rule done under VP-18085 as new reason `mixed_collection_methods`.
- 4-part: 目的 = API orders can never hold what the portal cannot build. 改前 = suffix heuristic
  + item_id equality; no menu concept. 改後 = section (not_at_home|at_home|both, from
  item.description) + dbs_mapping twins, both from the snapshot the portal renders. 改什麼 =
  CatalogMenuClientService (30-min snapshot, 60s miss-refresh floor, stale-on-failure, throw
  when none), findDuplicateTestCodes(menu) + findMixedMenuCodes, pricingBaseUrl() shared,
  fixture catalog-external-codes.json removed, catalog-menu.fixture.json (trimmed prod
  snapshot, 40 KB) added, failures/dto/docs updated. No new env var (Gate 4 n/a).
- Branch `feature/leo/VP-18085-menu-section` @ 9e98be5 (from origin/main 3c9aeba). NOT pushed.
- Tests: 142 in the 9 touched suites; full hl7-order-processing dir 1283 pass / 3 fail —
  the 3 are parser.service.spec prod-fixture NY-swap cases that ALSO fail on clean origin/main
  with the gitignored `test-data/prod-fixture/` present (verified in a throwaway worktree);
  unrelated. lint 0 errors; nest build ok.
- Live smoke (staging, dist classes, real productMap + real menu): NEURAL/WHEAT twin ->
  duplicate; NEURAL+FOOD_ZOOMER_DBS -> mixed; FOOD_ADDITIVES+_DBS -> mixed (section covers the
  dbs_mapping gap); GUT_ZOOMER(both)+either side -> placed; 3-code at-home+both -> placed.
  Menu: 341 sections, 20 twins, ~1.6 s cold for 8 cases.
- Behavior change to flag: NEURAL_ZOOMER + FOOD_ZOOMER_DBS now REJECTED (was placed = T3 negative
  control in round 1). This is the PH-870 / VP-17724 rule landing here.
- Open: portal also hides at_home items in serum mode by `section`, so 165+620 is impossible
  there too — parity holds. Bundle members vs standalone overlap still out of reach.

### [[VP-18194]] · _Decisions Made_

### [2026-09-22] Leo, Step 4 round 2 — SCOPE CUT
- **Cross-ticket rule (Leo, verbatim): "以前的不管了，只做未來的(這點很重要是accross ticket的)"**
  => no backfill, no re-delivery of anything already sent, for this or any other ticket.
- Consequence for VP-18194: the whole amended-redelivery mechanism is CUT. No nightly sweep, no
  `(is_amended, final_report_date)` comparison, no extra columns on `result_attachment_records`.
  An amendment that happens to re-fire the push (the result-re-approval class measured above) will
  re-deliver naturally; the report-content-only class is explicitly out of scope.
  => AC "An amended report triggers redelivery of all report PDFs for that order" is knowingly NOT
  implemented; must be stated to PM on the ticket, not silently dropped.
- Leo's statement of the feature, verbatim: "就是等report完成後去看說是不是要per report 發 pdf,
  如果是的話就發多個, 只是這樣".
- Agreed reading (stated to Leo, not objected): delivery happens at the push the integration already
  gets. Maristany and FOLLOWTHATPATIENT are WHOLE_ORDER, so in practice = one drop of N PDFs next to
  `{accession}.hl7` when the order completes. Per-report timing remains available by setting that
  integration's existing `result_push_level=PER_REPORT` — no new code, no new trigger.
- DDL therefore reduces to the 4 setting columns only (2 on `ehr_vendors`, 2 on `ehr_integrations`).
  `result_attachment_records` needs NO schema change: `attachment_type='REPORT_PDF'` + `file_name`
  (which carries the short name) is enough for audit and for the "already delivered -> skip" check.
- Open, non-blocking: whether Cerbo actually ingests a loose `.pdf` and files it against the right
  test. Unverifiable on our side. Plan: canary on Maristany (clinic 127660) only, then ask Terry for
  written confirmation. If they only consume `.hl7`, the HL7-embedded variant comes back as a new ticket.

### [[VP-18270]] · _Decisions Made_

- Leo 2026-09-14: "全部改成用 kit_delivery_option, 然後看一下有哪些是這兩個column不一樣的".
- No-integration fallback (API scope-only path, VP-17472) keeps behaviour: default `NON_BLOOD_ONLY` (== legacy kits_options 0).
- New enum value `BLOOD_ONLY` (never had an integer mapping) -> blood ship, non-blood supplied by clinic.

### [[VP-18406]] · _Lessons Learned_

### [2026-10-08] Leo: booked order still consultationEligible=true, and active_event_id is null
- `consultationEligible` is six-month-window only (ticket scope); "already booked" was never in the rule. Booked state rides on the separate row field `active_event_id`, which the FE gates on (`PatientTestAction.vue:32`).
- **`active_event_id` has been dead since 2026-05.** findPatient's `getEstimateTimev3` -> `calendarEventService.getSamplesEvents` reads MySQL `va_schedule.sample_event` (`PORTAL_CALENDAR_DATABASE_URL`, prod and st both 192.168.10.213:3306). From the prod trans pod via `.prisma/portal-calendar-client`: 20,719 rows, max created_at 2026-05-12, 0 rows in last 30 days, no row for LBS-1799's 2512016885. Bookings now land in Postgres `calendar_prod.v2_event_accession_claim` (transv2 `createEventByPatient` / `isAccessionClaimable`): min claimed_at 2026-05-06, 4,115 rows, 436 in last 30 days. trans v1 has a Postgres `ehr-calendar-client` (`EHR_CALENDAR_DATABASE_URL`, same DB/schema per env) but its prisma has no `v2_event_accession_claim` model. The `event-sync.service.ts` cron only syncs old `booked_schedule` -> `scheduler_event`, not v2 claims -> sample_event.
- Leo's test order 2610026002 (patient 3227472): claim 160 / event 14331 (2026-10-16 17:30Z) exists only in `calendar_dev_new` (staging transv2), not in calendar_prod.
- Only working "Consult booked" signal today is transv2 `accessionClaimStatuses` (VP-18050) in the Select Related Test modal; patient page / order history still rely on the dead `active_event_id`.
- Options reported to Leo: (a) leave eligibility as-is, (b) add `ALREADY_BOOKED` reason; either way `active_event_id` needs a real source (read `v2_event_accession_claim` via the existing Postgres client, batched by accession_ids).

### [[VP-18481]] · _Lessons Learned_

- Measure before theorising about a stall: a per-connection trace showed every hook done in 1 s; the "hook hangs" story survived one more PR than the evidence allowed.
- When the entrypoint is `npm run`/`nest start`, SIGTERM never reaches the app; when node becomes PID 1, any framework that re-raises the signal to finish shutdown hangs. Explicit `process.exit()` after `app.close()`, bounded by a deadline.
- MySQL `Aborted_clients` increments on Prisma `$disconnect()`; do not use it to judge shutdown cleanliness.
- `kubectl rollout status` returns before the old pod is gone; select the target pod by image + Ready + no deletionTimestamp.
- A permission fact in LTM is a world fact: check `gh api repos/... permissions` before saying "no access".
- LIS-Sample push gate needs node 22 (`~/.nvm/versions/node/v22.16.0/bin`) and installed node_modules; node 24 breaks the NestJS 9 CLI.

### [[VP-18589]] · _User Feedback_

### [2026-09-30] Leo, same session
- 「我看不懂你的回覆，重點是什麼？」 → the first customer-reply draft was too soft
  ("we'll let you know"); Leo wants the engineer's view: WHO owns each gap and WHY it
  exists, not promises.
- 「第三點是emr的問題嗎」 → confirmed both halves (staging shipping host empty by design;
  lookup has no core fallback) are emr-v2.
- 「ok 全部按照文檔先做完，然後給我回覆客戶的comment」 → treated as Step 4 approval for
  the derivation fix; the five doc-only fields are NOT implementable (dropped 08-13,
  no upstream data) — reported as a docs fix, not silently re-added.
- 「merged, 請等deploy 後測試，然後comment要改，先讓chris 改 doc, 再回報客戶」 → Leo
  merged #444 himself; order of operations: staging verify → Chris (PM) fixes the
  mintlify page → THEN the customer reply. Customer reply must not go out before the doc.

### [[VP-18714]] · _Decisions Made_

- Serve the PDF from emr-v2 rather than teach base-report partner tokens: keeps one guard, one
  scope rule and one withhold rule for the FHIR surface; base-report untouched.
- Public base derived from the request host (x-forwarded-host | host) + `/v1/report/fhir`;
  https unless x-forwarded-proto says http (pod only ever sees http). FHIR_PUBLIC_BASE_URL is
  an override only, deliberately not set in any CM (pre-push env guard flagged, recorded in PR).
- Withhold parity implemented by running enrichFromReportService + applyOrderCancellation over
  a shell, not by re-generating the HL7: cheap, and cannot drift from the FHIR body's rules.
- Upstream non-PDF answers (incl. base-report's 500 "not ready") -> 503, never forwarded.

### [[VP-18749]] · _Lessons Learned_

### [2026-10-08 ~19:30-20:30Z] PRs, stage_test merged, staging baseline
- #903 (draft, -> main, head 09dd834) and #904 (-> stage_test, head 5422b2b, cherry-pick -x; conflict in event.module.ts = keep settingTool + CalendarPrismaService). #904 CI green (typecheck + unit tests 3m44s), merged 2833633; staging deploy run 37827017894.
- Stage worktree needed its own `npm install`: stage_test-only deps `@zootools/email-spell-checker`, `tlds` are not in the main checkout's node_modules -> 10 suites fail to load and pre-push tsc fails. With its own install: 40/40 suites of those modules pass, pre-push build + DI smoke pass. `npm install` dirties package-lock.json + prisma2/generated -> `git checkout --` them before commit.
- Jira VP-18749 -> Dev In Progress (transition 3); Relates link to VP-18406. Comments are DRAFT ONLY (leo-working-rules: per-comment authorization).
- Leo's order 2610026002 is on STAGING core (prod lookup: no sample); the claim's `claimed_by user:54674` == the st pod's internal token (customer 9708 / clinic 10136, role ss), so the pod token finds it.
- Probe `scratchpad/fp-probe-18749.js` (POST 127.0.0.1:3190 /trans/findPatient, `flagged` must be boolean, search_patient_type accession_id). BEFORE on pod a9d5e74: total_count 1, accession 2610026002 active_event_id null, consultationEligible true, etd Unknown.

### [[VP-18749]] · _Lessons Learned_

### [2026-10-08 ~20:0x-21:0xZ] Prod deployed + verified; closing
- Leo merged #903 (386e6c3); prod run 37834531618 success; pods b99cc7bbc-* on 386e6c3 by ~20:03Z.
- Prod positive case NOT reachable with service tokens: claims (4,120, all practice 150105) belong to many customers; the three tokens in lis-trans-config (customer 9708 / 1870 / 27102, all clinic 10136, role admin != 'service' so no body override) have no claimed accession among the latest 600 (lisportalprod2 `lis_core_v7.sample` cross-check). Both tokens resolve to the same scope (identical 11,729-patient result) -> findPatient scopes by clinic.
- Prod evidence instead: (1) in-pod `.prisma/calendar-client` read of prod claims via the shipped image: 2512016885->13834, 2607256005->14345, 2608096021->14345, 2609256472->14341 (model + connection OK); (2) findPatient AFTER: 200, total_count 11,729 same as BEFORE, 67 rows, etd present on all (=> getEstimateTimev3 did not degrade, claim lookup did not throw); (3) 0 `"level":"error"` and 0 `getActiveClaimsByAccession` lines on all 4 pods.
- Datadog: prisma/Postgres spans are NOT emitted by trans v1 (only ioredis spans); pg_stat_statements not installed on the calendar PG. Neither can prove the query ran in prod.
- Tooling notes: `mcp__vibrant__lookup_sample_id` takes `accession_id` (and vice versa); `query_general_sample_events` returns customer_id/clinic_id per accession; `lisportal_mysql_query` = lisportalprod2 read-only, `lis_core_v7.sample(accession_id, customer_id)`. A `kubectl exec ... sh -c '...'` carrying any `rm` text trips the Bash safety check -> use `kubectl cp` + `kubectl exec -- env X=1 node file`.
- Jira: closing comment posted (Leo: 「測試後確認並且 done ticket」), transition 15 -> Done.

### [[VP-18833]] · _Decisions Made_

### [2026-10-14 21:20Z] Leo approved the plan; timing follows result_push_level
Leo: "1.ok 2.不對吧，這是要視需求。如果他要per report, 就需要各自先送，應該也有kafka message".
=> message SHAPE comes from the per-report-HL7 mode (split flag + HL7-only vendor); TIMING comes from
the existing result_push_level: PER_REPORT -> each report pushed on its own
`new_report_status_updated` Kafka event; WHOLE_ORDER -> all N at report_finished. The whole-order
push for a per-report-HL7 integration fans out into `REPORT:{SHORT}` scopes, and the existing
REPORT-scope dedup (TRANSMITTED blocks) skips reports already sent early -> the final push only
sends the remainder (also fixes the VP-17441 "last report never gets its own push" gap for this mode).
Approved: reuse `split_result_pdf_by_report` (no DDL); fail-closed fallback to the whole-order
message + combined PDF on any coverage/overlap/API failure, with an alert.

---

## Other / uncategorized <a id='other'></a>

### [[INCIDENT-20260518]] · _User Feedback_

### [2026-05-19] Leo 指認 PDF 下載要 3 分鐘 timeout 不要 60 秒
→ c6555a7 拉到 180s × 3 attempt。

### [[INCIDENT-2604156666]] · _User Feedback_

### [2026-05-21] Leo 強調：「未來在改這種東西一定要記得 前後的 end-to-end result 絕對不能變... 非常嚴重的錯誤」
- 已寫到 user-level memory `feedback_end_to_end_equivalence.md`
- 涵蓋：替換 RPC primary、升級 service、proto 一樣 ≠ marshalling 一樣（zero/null/empty 序列化差異）
- 動作要求：切換前必須跑 diff script 對 N 個 representative sample 比對前後 JSON output，邊界 case (missing/null/過去未來日期/空字串) 都要 cover

### [[VP-16945]] · _Decisions Made_

### [2026-06-09] UTC sentinel 是核心問題；解法在「unset 表示法」，非換來源
- Leo 質疑：若後端補 `!== 'UTC'`，真的在 UTC 的 provider 登入後仍被強制 PST，永遠改不了。**正確。**
- 我曾下「換來源讀新欄位」結論 → **Leo 否決，ticket 沒這樣寫、來源讀哪個欄位本來就還沒定（取決於 VP-16943）。撤回此結論。**
- 真正的根因與 Leo 質疑一致：**只要 `'UTC'` 同時代表「未設」和「真 UTC」就一定有人被犧牲。** `!== 'UTC'` 守衛是錯的（犧牲真 UTC）。
- 正解 = 讓「未設定」變成可與真 UTC 區分的值（與來源無關）：
  - legacy 那批「填不出值的 UTC」應轉成 **NULL**（NULL=未設→PST；`'UTC'`=真 UTC→顯示 UTC）
  - VP-16944 登入抓真實時區寫回同欄位；reminder 端 `value ?? PST`，**不需 `!== 'UTC'` 守衛**
- 與 VP-16943 (Fan) 要鎖死的真正只有一件：**provider 設定「未設定」用什麼表示，且絕不能是 `'UTC'`**（傾向 NULL）。來源讀哪個欄位次要。

### [[VP-17524]] · _Lessons Learned_

**zsh gotcha:** always quote `--include="*.java"` in `grep -r`. Unquoted, zsh fails the whole
command with `no matches found`, which reads exactly like "nothing in the codebase matches".

### [[VP-17685]] · _Decisions Made_

Call **v1**, do not patch v2. VP-17318 (2026-07-02) had already moved the order path off v2's
`GenerateSampleID` after finding it ~311k ids behind `lis_core_v7.sample`. v1 implements the same
proto shape with `moment.tz` on a `node:22` image. Patching tzdata in v2 would only make an unfit
dependency look usable.

### [[VP-17827]] · _Lessons Learned_

- **5 of 9 placed orders are mis-booked, all provider 43262 (Anna Emanuel, on 2930/8003/36290/144510).** Every
  43262 order lands on 2930 because `resolveOrderingIntegration` picks FULL_INTEGRATION-first / newest `updated_at`
  among the provider's LIVE ordering rows and 2930 wins. FTP3-7 (ORC-17=2930) is right by coincidence.
- Single-location providers (6263 Shah -> 8003, 38677 Perkins -> 142676) always land where ORC-17 says, which is
  exactly why Tom saw it only on 43262's orders.
- FTP3-4 / FTP3-8 / FTP3-9 are test patient "Tom Testington" (phone 6617427201, address test). FTP3-5/10/11/12 are
  real patients. The 2 non-archived rows (6575 07-09 VASC727501, 7266 10-06 VAREQUISTION471) are
  `emr_code_not_found`; 7266 still open and still not in any DailyJob triage.
- MSH-4 is the vendor's own org number (3, 13), not a Vibrant id, confirming 08-21's finding that MSH-4 is useless
  for this vendor and ORC-17 (== MSH-6) is the field to read.

### [[VP-18342]] · _Lessons Learned_

- A "not found" from an enrichment layer can hide a transport/decode error; always check the
  gRPC client log line before believing the business reason (LTM already said this for
  patient_not_found — this time it was true again and went unfixed for 13 days).
- Vendored proto copies need a consumer list: core-v2 wire-type fixes (VP-17437, VP-18064)
  only synced one of two downstream copies.

### [[VP-18344]] · _Lessons Learned_

- "Sync a vendored proto dir" must include a load check of every runtime entry file: byte-copying the
  files that already exist misses NEW transitive imports (lis_main.proto -> notification.proto).

### [[VP-18463]] · _User Feedback_

### [2026-10-13 23:45Z]
- Leo: Jira writes must use his account (Atlassian MCP), not the vibrant MCP service account.

---

## Production safety / kafka / email / SFTP <a id='prod-safety'></a>

### [[INCIDENT-20260518]] · _User Feedback_

### Leo 明確否決方向（記得別再提）
- **不要再建議 emr-v2 切到 non-detailed batch** — Leo 強調 detailed 欄位（_l1~l6 abnormal level）對 HL7 有用，這條路否決了。

### [[LBS-1784]] · _Lessons Learned_

- NPI is not a customer identity in lis_core: bind prod writes to customer_id; use NPI only for
  discovery/reporting. Guard "exactly one row by customer OR NPI" is wrong for order_clients.
- Removal leaves result_enabled=1 on a REJECTED row — fine for the gate, but a future "reactivate" must
  not assume result_enabled reflects intent.

### [[VP-17591]] · _Decisions Made_

Leo: **file wins; if absent use DB** — then narrowed for NY:
> 有 Gut Zoomer（或任何需要判別 NY 的測試）一律只能以 HL7 為標準，沒有就連 DB 都不看直接拒單。
> 多收錢的問題一定要 customer 提供完整訊息，否則因搬家等原因會有財務問題，不能到我們這裡。

### [[VP-17827]] · _Lessons Learned_

**Verification gap.** The 7 orders from 09-16 onward (ids 7123..7266) were NOT re-checked at the raw HL7
level today: the AKS pod has no `/EMR_storage/.../FOLLOWTHATPATIENT/Prod/Order/archive` (intake runs on
the on-prem pod, ns default), vendor SFTP 64.124.9.100:2224 times out at handshake from AKS and is
unreachable from this machine, and on-prem 192.168.60.5 is unreachable without VPN. Re-run the archive
read from the on-prem pod before telling Tom "always".

### [[VP-17827]] · _Lessons Learned_

**Tooling notes.** `mysql` CLI is not installed on this machine; `node` + emr-v2's `mysql2` works locally
only with VPN. The pod path that worked: `kubectl cp` a 15-line node script that `require`s
`/app/node_modules/@prisma/client` and runs each `;`-separated statement with `$queryRawUnsafe`,
`JSON.stringify` with a bigint replacer. `hl7_file_input.order_input` is the placed-order JSON (has
`clinic_id`, `patientId`, `sampleId`), not the raw HL7. The lis_emr user sees only the lis_emr schema.
Scratch secrets (vendor SFTP password, my.cnf) and the pod `/tmp` scripts were deleted at the end.

### [[VP-17827]] · _Lessons Learned_

VP-17827 transitioned Dev Complete -> Done (transition 15) on Leo's instruction without waiting for the first live
FTP order. The post-release check in the previous section is still worth doing opportunistically (daily hl7_fail
triage will see the next FOLLOWTHATPATIENT row); if it fails, reopen as a bug. Guard-ticket idea declined by Leo
(2026-10-08) — do not re-propose unless a second multi-practice provider appears under a vendor not in the map.

### [[VP-17868]] · _Decisions Made_

- Option A.
- Date disclosure is gated: `isClaimable` accepts any accession id and never verifies it belongs to the caller's clinic, so an ungated date turns the query into a probe for other practices' bookings. Disclose only when `claimed_by` matches the caller's user id, or the caller is the holding event's creator / a participant (provider calendars in 150105 carry `calendar_owner_id = customer_id`).
- `supportEmail` is passed as an interpolation param, not baked into the message: vue-i18n (v11) reads `@` in a message body as linked-message syntax. Repo has both a raw `Support@vibrant-america.com` value and a `support@@vibrant-america.com` one, i.e. no reliable precedent.
- Dropped the Alert's hard `:height="42"` on this alert only — the longer copy wraps to 2-3 lines and the fixed box clipped it.

### [[VP-18303]] · _Decisions Made_

- **Leo 2026-09-17: the endpoint must wait and return a real answer.** Default is synchronous
  (unchanged from today, still 201 — I did not convert it to a literal 200, that would be a
  gratuitous contract break; flagged for him to override). `async: true` selects the 202.
- No machine callers exist — grepped every repo under `~/src`, the only references are
  runbooks/docs and this repo's specs — so either default was safe to choose.
- `generate/batch` and `generate-content/:sampleId` untouched (the latter must return HL7 inline).
- Did **not** fix the two side-findings below; they are separate tickets.

### [[VP-18749]] · _Lessons Learned_

- Two scheduling systems coexist in calendar data: old MySQL `va_schedule` (sample_event/booked_schedule) and Postgres
  `calendar_prod` v2 tables. Any "is this accession booked" read must go to `v2_event_accession_claim`.
- `psql` masking with sed `s/:\/\/[^@]*@/` leaks when the password itself contains `@`; mask with a stricter pattern.

---

## Error handling / throw / log / silent <a id='error-style'></a>

### [[INCIDENT-20260601-sftp-hang]] · _Lessons Learned_

1. **Any `await network.close()` in a Node.js singleton MUST have a timeout + force-destroy fallback.** Otherwise misbehaving peer locks the entire service.
2. **Singletons that wrap network handles** become single points of failure. Prefer per-caller instances or a pool with explicit acquire/release semantics.
3. **`finally` block does NOT run if the preceding `await` never resolves.** Always clear shared mutable state BEFORE the await, not in `finally`.
4. **k8s livenessProbe is the safety net** — without it, a process that hangs in user-space but keeps the TCP socket alive will never be restarted by k8s automatically.

### [[VP-17524]] · _Lessons Learned_

**技術面 — a mapping table over a vocabulary you do not own will always be short.** This mapper
enumerated the tag values that had been observed. That is fine while the producer is you; it is a
latent bug when the producer is another team's pipeline. The port from Java changed the contract
without anyone noticing: Java *derived* the class from the value, emr-v2 *trusts a label*. When
that shift happens, prefer structural normalization (strip known modifier prefixes/suffixes, then
match the base) over adding one more `case` each time prod screams. Keep the loud fallback: the
`default:` ERROR log is the only reason this bug was ever visible.

### [[VP-17584]] · _Lessons Learned_

- A done-category status whose *name* is not "Done" defeats both the closeout JQL and
  `reconcile-jira.py`. Match on `statusCategory`, never on the status name. Fixed in
  `scripts/dream.md` (PR #41).
- "Ticket closed without the work being done" and "work done under a sibling ticket" produce
  the same Jira surface: a done-category status, no comments, no PR. Only ground truth
  separates them, and here the pessimistic reading would have been wrong. Check the sibling
  ticket's STM before concluding a closure was hollow.
- When a ticket is superseded because its deliverable got absorbed into another session, say
  so *on the superseded ticket*. One comment ("done under VP-17544, program id=40") would
  have made this audit a two-minute read instead of a reconstruction from prod data.
- `beta_program_participations.added_by` is free text: it holds a user id ("54674", which is
  `TokenHelperService.DEFAULT_USER_ID`, i.e. a service token rather than a person) in one row
  and a ticket id ("VP-17851") in the next. Do not resolve it as a user id without looking.
- An audit window tied to wall-clock time silently loses everything that happened while the
  auditor was down. Tie it to the last successful audit instead.

### [[VP-17628]] · _Decisions Made_

### [2026-08-06] Leo direction
- Leo confirms the system HAS an existing setting called "default provider" — use it as the fallback source. Rationale: no API is exposed today for managing/listing provider ids under a clinic, so partners can't discover valid ids.
- Leo decision (2026-08-06 earlier, SUPERSEDED): unset → fall back to token customer (portal parity).
- **FINAL ruling (Chris Wu via Leo, 2026-08-06 15:05, supersedes the above)**:
  1. defaultProvider NOT set → omitted-provider call **errors** (no token-customer fallback).
  2. defaultProvider set → omitted-provider call uses the default provider.
  3. providerId explicitly supplied → overwrites/wins; order placed under the supplied provider. (My reading: priority ordering only — the existing token cross-check for explicit ids stays, per ticket "if provided, behavior unchanged". Stated to Leo for correction.)
  4. Junjie Lin will add a popup at API-credential generation forcing partners to set default provider → unset becomes rare for new API clients (mitigates the 63%-unset stat for the partner population).

### [[VP-17827]] · _Lessons Learned_

**What this means for Keith's ask.** Follow That Patient does not need a new field: on the orders whose raw
HL7 we examined (07-11, 07-16, 08-01; STM HL7-NPI-PRACTICE-MATCH-20260820 + reference/
hl7-practice-vs-sent-clinic-mismatch-20260821.csv) MSH-6 and ORC-17 both already carry the Vibrant
clinic_id of the ordering location, and 07-16 (sample 2597376, HL7 said 36290, we placed 2930) is the
proven misroute. The ask to Tom should be a confirmation (both fields always = Vibrant Practice ID of the
ordering location, for every location, value follows the location not the provider), and ORC-17 is the
field to standardise on if anything moves. Our side of the work (read ORC-17, use it to disambiguate among
the provider's clinics, layered on top of ORC-12, never replacing it) is VP-17827 approach A/B and is still
gated on the Sherry/Junjie fallback decision + VP-16164.

### [[VP-17827]] · _Lessons Learned_

**Results (DB + pod log, 20:15:08Z).**
- 2245 T1: log `[practice-id] vendor=FOLLOWTHATPATIENT provider=4769 practice=134410 -> customer 4769 clinic 134410`;
  `order_input.clinic_id=134410`, sample 2554429 (dev core), parse_finished 1. Decoy NOT chosen -> practice filter beat
  type-rank/recency live.
- 2246 T2: log `… practice=777001 not among the provider's ordering practices [134410,134409] — order held as
  practice_not_found`; `last_error=practice_not_found=4769@777001`, `customer_not_found=4769@777001`, retry_num 2->1,
  parse_finished 0, no sample. Retryable path confirmed end to end.
- Fallback (blank / unconfigured vendor) covered by unit tests only; not replayed live to avoid placing a decoy-clinic order.

---

## DB / SQL / FK vs derived column <a id='db-style'></a>

### [[LBS-1828]] · _Lessons Learned_

- LBS-1799 playbook replayed end to end in one session with zero new code; the only moving parts were ids (customer / clinician calendar / owner) and the live slot. Keep `pg.sh` + `mint.js` + `gql.sh` as the standard kit for this class.
- `lis_ordermanage.orders.id` is a 17-digit id: comparing it to an unquoted numeric literal in MySQL returns neighbouring rows (float collapse). Always quote it.
- `v2_schedule.weekday` numbering could not be inferred from the rows alone (events exist outside the apparent slots because staff `createEvent` bypasses validation); use live `getProviderAvailability` as the only source of truth for "earliest slot".

### [[VP-17827]] · _Lessons Learned_

**Draft.** `drafts/VP-17827-prospera-practice-id-reply-20261007.md` (Leo's voice, to Tom cc Robin/Keith/
Xiaoye, with the 33-row Practice ID table). Blank Provider cells must be filled or the column dropped before
sending.

---

## Testing / mock / verify <a id='test-style'></a>

### [[LBS-1785]] · _Lessons Learned_

- Cloud core gRPC mirror address in LTM (10.224.0.199:30276) is stale since INCIDENT-20260908; use 10.224.0.10:30276. `scripts/get-customer-rpc.ts` is broken by a stale `scripts/node_modules` (protobufjs fetch missing) -- run grpc-js from the repo root node_modules instead.
- Ticket text claimed duplicate result transmission was possible; code (dedupe by emr+result_path) says no. Verify claims about pipeline behavior against code before repeating them in the closeout.
- macOS has no `timeout`; use the Bash tool timeout parameter.

---

## Review flow / report format / approval <a id='review-flow'></a>

### [[VP-18342]] · _Decisions Made_

- Leo 2026-09-22: file a ticket for fix 1 only (proto sync so emr-v2 can read core-v2 data);
  routing fix (root cause 2) stays a noted follow-up. Ticket VP-18342 created via the
  claude.ai Atlassian connector (vibrant MCP create_jira_issue returned 403). VP Bug create
  screen requires Detection Method / Environment / Portal Affected System-Page / Impact / Due
  date — set Customer Report / Staging / EMR / Significant-Large / 2026-09-29.

---
