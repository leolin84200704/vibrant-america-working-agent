---
id: SANDBOX-SEED-W2W-20261005
type: stm
category: pm_patterns
status: waiting
score: 0.0846
base_weight: 0.7
created: 2026-10-05
updated: 2026-10-07
links: []
relations:
  unblocked_by: []
  blocks: []
  sibling:
  - VP-18589
  - VP-18593
  - VP-18595
  - VP-18596
  - VP-18714
unblock_when: (1) shipping team answers Chris whether a staging shipping service can
  be exposed to AKS staging and seeded for accessions 2610016001-2610016011 → set
  GRPC_SHIPPING_HOST/PORT on staging ConfigMap and re-run m-list.js; (2) report team
  (Yekai) re-seeds M06 preliminary on the TRUE staging report service + builds the
  M07 PDF in base-report-dev pdf-cache; (3) Leo decides the partner PDF download path
  (presentedForm url = base-report pdf-cache, rejects API keys) and whether a
  delivery-exception signal should exist in the payload (M09/M10); test = the 11-row
  list/lookup table
tags:
- sandbox
- w2w
- get-orders
- kit-status
- seed-data
- chris
- yekai
- leo-reply-style
- vp-18683
- pdf-presentedform
summary: Integrator (via Chris Wu, with Yekai Liu) asked us to seed 11 sandbox orders
  (samples 2554394–2554404, customer 50687) into target GET /orders states. Recipe
  per order (core order_kit_status / sample_received_time / report service) drafted;
  kit block impossible in sandbox (no shipping). Leo's final reply recorded verbatim.
---

# SANDBOX-SEED-W2W-20261005 - Work Loop Record

## Ticket Analysis

### [2026-10-05] Request
Chris Wu (Slack, Simplified Chinese): 「需要给用户造一套数据这里 @Yekai Liu @Hung-Fan Lin」
with the integrator's table M01–M11 (placerId W2W-…, sample 2554394–2554404, target
state). M09/M10: "please use whatever value production returns for these cases".

Current sandbox state (staging pod sweep, customer 50687): all 11 exist, accessions
2610016001–2610016011, all status kit_delivered (staging core marks every order
kit_patient_received_kit); M02 and M06 already have a preliminary report → lookup
analyzing. kit null on all (no shipping service on staging).

Feasibility (lookup derivation on staging = core fallback ladder + report service):
- kit block (kit.status/carrier/trackingNumber/shippedAt/deliveredAt): impossible in
  sandbox — data lives only in shipping (FedEx label + scans); sandbox orders never
  entered shipping. Only `status` can be produced.
- M02 in_transit: shipping's 8-value kit_status has no in-transit value; FedEx Track
  API does (IT/AR/DP/OD) and LIS-transformer `getFedx` + LIS-Shipping `kitTrack`
  already call apis.fedex.com/track directly (consul shipping secret
  FEDEX_PRODUCTION_API_KEY/SECRET). emr-v2 could do the same (cache 10–15 min, only
  in-flight kits) — NOT decided; Leo told Chris 建議拿掉 for now.
- Recipe: M01 kit_lab_shipped_kit; M03/M08 keep kit_patient_received_kit; M04/M10
  kit_sample_shipped_back; M05 sample_received_time; M06 already preliminary;
  M07 report 'Final Report Available' + generated report; M08 + sample-level issue
  named *redraw* (→ exceptions redraw_needed); M09 kit_delivery_exception (prod answers
  kit_shipped; M10 prod answers sample_in_transit); M11 kit_lab_shipped_kit, they cancel.
- Core writes happen via core's `processShippingStatusUpdate` (KIT_STATUS_FLAG_MAP) —
  something on staging already emits PATIENT_RECEIVED_KIT; core/report data is
  Yekai's side, emr-v2 does not touch those DBs.

## Decisions Made
- Leo sent the reply himself (below). Our part: run the 11-row list/lookup table once
  the data is in and post it.

## User Feedback

### [2026-10-05] Leo's reply to Chris — VERBATIM (Leo: 「請記得我是怎麼回的」)
```
sandbox 沒有 shipping 服務，kit.status、carrier、trackingNumber、shippedAt、deliveredAt 在 sandbox 會顯示null(sandbox 的訂單沒有進過shipping)，只有 status 能做出來。M01/M02/M03 在 sandbox 看不到kit.status。M02 的 in_transit 在 prod 也不存在（shipping 沒有對應狀態,建議拿掉)
其他各筆要放的資料：
- core order_kit_status：M01 kit_lab_shipped_kit、M04 kit_sample_shipped_back、M09 kit_delivery_exception、M10 kit_sample_shipped_back、M11 kit_lab_shipped_kit；M03/M08維持 kit_patient_received_kit
- core sample_received_time：M05 填一個時間
- report service：M06 已經回Analyzing 不用動了、M07 Final Report Available 並產一份報告、M08 加一個名稱含 redraw 的 sample-level issue
- M09 在 prod 會回 kit_shipped、M10 會回 sample_in_transit，sandbox 放上面的值就會一樣
```
How it differs from my draft (style to reuse when drafting PM-facing text for him):
- Took my structure (限制先講 → 每筆要放的資料 → prod 對照) but compressed to one
  paragraph + one bullet list; no greeting, no names, no 「資料放好通知我」 closing.
- States the reason inline in parentheses right after the fact
  (「會顯示null(sandbox 的訂單沒有進過shipping)」) instead of a separate sentence.
- Precise about WHAT is invisible: 「M01/M02/M03 在 sandbox 看不到kit.status」 (not
  "看不到" wholesale) — he accepted that correction.
- Dropped my option list for M02 (拿掉 / 併到 M01 / 接 FedEx) to a single
  「建議拿掉」; keeps shipping-side asks out (does not ask shipping to add anything).
- Took the correction 「M06 已經回Analyzing 不用動了」 in his own words.
- Field names / values in English inline, everything else Chinese, no bold, no code.

## Code Changes

### [2026-10-05 14:22 PT] Staging core DB seed (Leo: 「請你直接造假數據(改db)」)
- Where: staging core v1 = deployment `lis-core-staging` (ns default, NodePort 30282),
  DB from its configmap `lis-core-staging-config` DATABASE_URL →
  **lisportalprod2-testdb.mysql.database.azure.com / lis_core_v7** (user lis_core_emr).
  NOT the on-prem .11 lis_core_v7 (LTM was right that .11 is not it). Ran Prisma raw SQL
  from inside the core staging pod (`/app/node_modules/@prisma/client`, DATABASE_URL
  from pod env) — no credential handling on my side. NOTE: the configmap dump prints
  the password inline in DATABASE_URL; redact by value, not only by key name.
- Core table shapes: `sample` (sample_id, accession_id, order_id, sample_received_time);
  `order_info` (order_id, customer_id, order_kit_status, order_report_status,
  order_status, order_cancel_time). Not `sample_data` (that is shipping's schema).
- BEFORE (all 11): order_kit_status kit_patient_received_kit, order_report_status
  report_not_ready, order_status order_processing, sample_received_time NULL,
  customer 50687. order_ids: 2554394→11405498, 2554395→11405500, 2554396→11405497,
  2554397→11405499, 2554398→11405501, 2554399→11405502, 2554400→11405503,
  2554401→11405504, 2554402→11405505, 2554403→11405506, 2554404→11405507.
- WRITES (WHERE bound to order_id + customer_id 50687 + explicit id list; 7 rows, 7
  expected): 11405498 kit_lab_shipped_kit (M01); 11405499 kit_sample_shipped_back (M04);
  11405501 kit_lab_received + sample 2554398 sample_received_time = 2026-10-05T21:22:32Z
  (M05); 11405505 kit_delivery_exception (M09); 11405506 kit_sample_shipped_back (M10);
  11405507 kit_lab_shipped_kit (M11). Untouched: M02 (Leo told Chris to drop it; it
  already answers analyzing via a preliminary report), M03/M08 (keep delivered), M06
  (preliminary → analyzing already), M07 (needs a generated report — report pipeline,
  not a DB flag).
- Reverse audit: 0 other 50687 orders carry any seeded value. Readback 11/11 as above.
- Rollback: set the six order_kit_status back to kit_patient_received_kit and
  sample 2554398 sample_received_time = NULL.

### [2026-10-05 15:10 PT] Readback after seed + handoffs
- Staging API readback: M01 kit_shipped, M04 sample_in_transit, M05 sample_received
  (lab true), M09 kit_shipped, M10 sample_in_transit, M11 kit_shipped; M03 kit_delivered,
  M06 analyzing unchanged; M02 analyzing (dropped); M07 kit_delivered (needs a generated
  report — report_available is computed from finished reports, not a flag); M08
  kit_delivered with no exception. kit block null on all 11.
- M08 blocker found: staging base-report's `GRPC_ISSUE_ADDR` =
  lis-issue-system-service.issue:30071 = **prod** issue system, although
  lis-issue-system-service-staging (:30072) exists. Seeding a redraw issue for staging
  sample 2554401 would land in prod (a real patient's sample id). Not done; report team
  must repoint staging first.
- Leo sent Chris (1) the M07/M08 → report team handoff and (2) the shipping ask
  (staging shipping service exposed to AKS + PO/tracking rows for the 11 accessions;
  fallback = emr-v2 sandbox synthesis behind a staging-only flag, not decided).
  Both sent 2026-10-05 ~15:05 PT (「done」). Waiting on their replies.

### [2026-10-07 PT] Integrator follow-up (English, via Chris) — ground truth re-checked
Integrator's five points vs staging (in-pod list+lookup, 11/11 matched, and code on
origin/staging):
- "orders have no kit" — still true, kit null on all 11; shipping ask (10-05) has no
  answer I can see (Slack not readable from here; Leo to confirm). No emr-v2 change.
- M02 "need kit + kit.status in_transit" — status is now kit_delivered (10-05's
  `analyzing` was the colliding PROD order read through base-report-staging-service;
  Yekai repointed to base-report-dev-service 10-06 01:42Z, VP-18683 comment 190706).
  kit.status vocabulary = not_shipped | shipped | delivered only
  (order-status.derivation.ts deriveKitBlock; 'in_transit' reserved, no raw value maps
  to it). Leo already told Chris to drop M02 — the integrator was evidently not told.
- M09/M10 "how do we know it is a delivery problem" — they cannot, by design today:
  DELIVERY_EXCEPTION ranks with shipped (OUTBOUND_RANK/RETURN_RANK = 1) → status
  kit_shipped / sample_in_transit, kit.status 'shipped' + trackingNumber, no
  exceptions[] entry ("the documented lifecycle has no exception slot", VP-18589).
  The only signal is the carrier tracking page. Adding a value = product decision.
- M06 "still kit_delivered, not analyzing" — CORRECT. Same root cause as M02: the
  preliminary report that made it `analyzing` lived in prod data. Yekai offered in
  VP-18683 comment 190706 to re-seed it on the staging results side; nobody has
  answered him. report={registered,0/1} now.
- M07 "PDF links point to api.vibrant-wellness.com, cannot open with sandbox keys" —
  presentedForm[].url = `${VIBRANT_API_BASE_URL}/pdf-cache/download/{accession}?style=`
  (fhir-result.service.ts attachPdfPresentedForm + hl7-to-fhir.mapper), i.e. staging
  https://api.vibrant-wellness.com/v1/lis/base-report-dev-service/pdf-cache/download/2610016007?style=advanced
  and prod .../v1/lis/base-report-service/... — same gateway host in BOTH envs; the
  link is base-report's own endpoint behind base-report's JwtAuthGuard (portal JWT),
  not the partner gateway. In-pod probe 10-07: no token → 401; CM VIBRANT_API_TOKEN
  (prod-signed) → 401; staging HS256 dev token → 500 "report might not be ready yet"
  (PDF not built in base-report-dev pdf-cache for 2610016007 even though
  getReportStatusListV2 says Final 1/1). So: (a) partner API keys can never open the
  link, sandbox OR prod — product gap, no partner-key PDF path exists in emr-v2
  (no proxy route); (b) on staging even an internal token gets 500 → report team.
  Not verified: whether the sandbox FHIR body for 2554400 carries Observations now
  that Yekai seeded 296 lis.test_result rows (FHIR needs an RS256 50687 token; the
  pod restarted 21h ago so the integrator's calls are not in the logs).
- M08 (not raised by them): redraw_needed exception present (VP-18683 done 10-05,
  emr-v2 #462→staging/#463→main, LIS-Report #1007 prod: real redraws now surface).
- M03 (not raised): two staging billing_issue exceptions — staging issue system noise.
- Jira: VP-18683 (Yekai, Done) is the only ticket for this seed work; QH-7500 twin.
  Atlassian claude.ai MCP returns 403 "app is not installed" today; vibrant MCP works.
- Ops note (Yekai, same comment): Jenkins copies AKS default/lis-emr-v2-config into
  ns emr-v2 + on-prem on every deploy and ignores k8s/environments/staging/
  kustomization.yaml → staging CM edits must go into the `default` ns copy.
- Draft reply (English, Leo's voice) in drafts/SANDBOX-SEED-W2W-reply-20261007.md.

### [2026-10-07 10:50 PT] M07 PDF link fix — emr-v2 PR #466 merged to staging (Leo: 「先把link改好，確認在staging 可以連上」)
- Branch feature/leo/fhir-pdf-proxy (worktree .worktrees/fhir-pdf off origin/staging 827126d),
  commit f5511ce, PR #466 → staging, self-merged 8a0efc0 (Leo's 10-03 staging-merge rule).
- 4-part: 目的 = partner API key 打得開 presentedForm 的 PDF link；改前 = link =
  `${VIBRANT_API_BASE_URL}/pdf-cache/download/{acc}?style=` (base-report portal guard, 401 for
  partners in BOTH envs; mapper `pdfDownloadUrlBase` + service attachPdfPresentedForm +
  bindAuthorizedAccession regex); 改後 = link = `https://{x-forwarded-host|host}/v1/report/fhir/{acc}/pdf?style=`
  served by emr-v2 `GET fhir/DiagnosticReport/:id/pdf` behind FhirAccessGuard + isAuthorizedForSample
  + the SAME withhold rules (enrichFromReportService + applyOrderCancellation over a shell; serve only
  when presentedForm survives and status final/corrected/preliminary); bytes proxied from base-report
  with the env-signed admin token (VP-18673 mintReportServiceToken), arraybuffer, 90 s, %PDF- magic;
  denied → 404 same message as DiagnosticReport, withheld → 404 "(report status: X)", upstream → 503.
- Ingress needs NO change: lis-emr-v2-fhir-short-ingress rewrites `/v1/report/fhir(/|$)(.*)` →
  `/api/v1/fhir/DiagnosticReport$1$2` (hosts api / api-sandbox / api.sandbox .vibrant-america.com;
  staging alias api.vibrant-america.com/v1/report/staging/fhir). Pre-deploy probe via api-sandbox
  with the QA (Adam) beta client (customer 50661, creds ~/src/credential/beta-clients-sandbox-20260729.md):
  `/v1/report/fhir/2608146008/pdf` → Nest "Cannot GET /api/v1/fhir/DiagnosticReport/2608146008/pdf"
  = sub-path passes through. Scratch verify script: scratchpad/sandbox-verify.sh.
- New optional env FHIR_PUBLIC_BASE_URL (override only; documented in .env.example +
  k8s/base/configmap.yaml, deliberately NOT added to live CMs — pre-push env guard flagged it,
  recorded in PR body). Mapper option renamed pdfDownloadUrlBase → pdfUrl builder.
- Tests: fhir-result 10 suites/156 green (new fhir-public-url.spec, getReportPdf cases, controller +
  routes coverage); pre-push related 23 suites/340 + DI smoke OK. eslint 0 errors (148 pre-existing
  `any` warnings).
- Live 200-path on staging is blocked twice: (a) needs a customer-50687 sandbox token (W2W's client,
  api-product holds it; the 5 beta clients are 50657–50661); (b) base-report-dev pdf-cache answers
  500 "not ready" for 2610016007 even to an internal token → Yekai must build the PDF. What CAN be
  verified post-deploy with the QA client: own accession → 404 withheld "(report status: registered)"
  envelope; 2610016007 → 404 "no accessible DiagnosticReport" (denied), FHIR body link shape.
- Not a ticket yet: commit/PR tagged [SANDBOX-SEED-W2W]; ask Leo whether to open a VP ticket.

### [2026-10-07 11:25 PT] M07 link fix verified on staging; ticket VP-18714 opened for Leo
- Staging pod 768487c9dc-kmcxn (image 8a0efc0) up ~11:10 PT. Live via api-sandbox with the QA
  beta client: own accession 2607296024 FHIR final/296 results, presentedForm links now
  api-sandbox.vibrant-america.com/v1/report/fhir/2607296024/pdf?style=…, PDF route 200
  application/pdf 7.5 MB / 7.1 MB; registered accession -> 404 "(report status: registered)";
  W2W 2610016007 -> 404 denied (same message). Details in VP-18714.md.
- M07 end-to-end still open: Yekai must build the PDF in base-report-dev pdf-cache (500 not ready)
  and someone with the W2W 50687 sandbox client (api-product / integrator) must retry.

## Failures
- My first explanation said "in_transit 在 prod 也不存在" without qualifying that it
  is shipping's vocabulary, not FedEx's — Leo pushed back twice (「我們不是有fedex API
  嗎？」「我以為我們有自己接fedex api?」). Say which system's vocabulary a limit
  belongs to; "we" includes LIS-transformer, which calls FedEx directly.
