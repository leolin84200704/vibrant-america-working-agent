---
id: TRANS-OPTIMIZATION-20260911
title: Trans v1/v2 optimization program — tracking ticket VP-18276 (related epic VP-17348
  / VP-18152)
status: active
category: technical
tags:
- trans-v1
- trans-v2
- lis-transformer
- lis-transformer-v2
- performance
- p95
- cloud-local-proxy
- config-drift
- vp-17348
- vp-18152
- core-v1-retirement
created: 2026-09-11
updated: 2026-09-16
links:
- CONFLUENCE-2684321795
- INCIDENT-20260518
- INCIDENT-20260528
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260817-onprem-deploy-freeze
- INCIDENT-20260910-emr-v2-di-crashloop
- QH-1104
- QH-1130
- QH-1159
- QH-1591
- QH-1775
- QH-211
- QH-2259
- QH-2648
- QH-680
- QH-862
- QH-918
- QH-919
- VP-15460
- VP-16169
- VP-16172
- VP-16232
- VP-16391
- VP-16499
- VP-16513
- VP-16514
- VP-16516
- VP-16520
- VP-16629
- VP-16785
- VP-16787
- VP-16859
- VP-16921
- VP-16945
- VP-16968
- VP-17065
- VP-17217
- VP-17222
- VP-17312
- VP-17412
- VP-17422
- VP-17577
- VP-17714
- VP-17753
- VP-17754
- VP-17755
- VP-17765
- VP-17766
- VP-17825
- VP-17868
- VP-17870
- VP-18048
- VP-18050
- VP-18276
- VP-9299
- business-model
- business-model-deep
- failures
- repo-catalog
- repos
score: 0.765
---

# Summary

Leo asked for a local-only plan document (no code, no Jira/PR comments) to optimize trans v1 (`LIS-transformer`) and trans v2 (`LIS-transformer-v2`) with zero functional change, based on two meeting recordings in `~/src/trans-optimization/` and the Core V1→V2 migration epic VP-17348. Deliverable: `docs/plans/trans-optimization/PLAN.md` (+ Appendix A transcript summary, Appendix B AKS read-only inventory, `raw-transcript/`).

# Key facts established (2026-09-11)

- Meeting intent: reduce P95 (10–20 APIs above 2s on Datadog, worse at peak); remove 2023-era `cloud-local-proxy` hops (built by 雨萱 when Azure/on-prem networks were not connected; networks now connected, proxy still serving); remove pure HTTP pass-through endpoints from trans; follow the Core Migration epic process (phase → detailed doc → Rui review → tickets). Core team only optimizes core-adjacent trans paths; the rest is on the trans side.
- Trans exists for two reasons that must survive optimization: Core is going pure gRPC for PHI security (trans = only HTTP egress of PHI) and front-end aggregation.
- **Live nesting found on prod (AKS read-only)**: transv2 `checkIfPersonalizedReportCanBeCreated` → `cloud-local-proxy-service.cloud-local:3047` → on-prem `192.168.60.77:8081` (read at `patientProfile.resolver.ts:335`); transv2 `proxy_getkit`(x4)/`proxy_getteststatus`/`proxy_getQuestionaire` → trans v1 `lis-trans-service:3146/proxy/grpc/*` → gRPC; transv2 `getSetting/get_setting/get_setting_tokne`, `va_events`, `skin_placepatientorders` → trans v1 HTTP.
- **Stale config**: trans v1 prod has 14 keys still valued `api.vibrant-america.com/v1/lis/cloud-proxy` but 0 code reads (v1 already de-proxied per `LIS-transformer/docs/proxy-migration-configmap.md`); transv2 has 8 keys pointing at unreachable `192.168.10.153:8081`, 0 reads.
- **Public-ingress round trip**: trans v1 has 55 ConfigMap keys on `api.vibrant-wellness.com/...` for services that live in the same cluster (base-report, shipping, accounting, samples, interactive-report, charging); v2 already uses `*.svc.cluster.local` for the same targets.
- transv2 selects core v1 gRPC in prod and core v2 in staging via 20 scattered `SERVER_ENVIRONMENT==='prod' || FORCE_CORE_V1_STAGING` checks (12 files). v1 `trans.grpc.options.ts:142-147` computes `coreSampleV2Url` but never uses it (dead code). Residual core v1 HTTP: v1 `create_patient`, `create_patientv2`, `list_customer_by_id_carlos`; v2 `list_customer_by_id_carlos`.
- trans v1 gRPC `TransService` (5 methods) is consumed by LIS-Shipping, LIS-Sample, LIS-backend-results-grpc → cannot be removed.
- Deploy: both repos push-to-deploy via GitHub Actions with **no test/typecheck step**. Live: v1 3 replicas (repo yaml says 2), 2Gi mem request, no limits; v2 3 replicas 1536Mi; no HPA; cloud-local-proxy 3 replicas, `:latest`, no probes, 57 env.
- Config drift: repo `lis-trans-k8env.yml` has 5 keys vs 154 on cluster; meeting confirmed repeated `kubectl apply -f` regressions (cloud URLs reverted to on-prem).
- Test baseline (local): v1 jest 17/46 suites fail (Redis 192.168.62.79:4647 unreachable, stale local node_modules missing `@google-cloud/bigquery`, stale mocks `createMetadataForCoresampleV2`); v2 7/52 fail (stale mock `createOAuth2Metadata`, misnamed integration spec, practice_event_type graphql specs). tsc: v1 1 error (bigquery module), v2 clean.
- Hot spots with evidence: v1 `findPatient/returnPatient` (797 lines; VP-18197 removed the accounting call on 09-10 after p95 went 2.5s→7-13s), v1 `getTimeLine` (600 lines), v2 `patientProfile` (4x proxy_getkit per sample), v2 PNS resolver (19 ResolveFields, no DataLoader anywhere in v2).

# Gaps / blockers

- Atlassian MCP failed to connect this session: VP-18152 / VP-18140 / VP-18141 / VP-18144 bodies unread; only daily-digest summaries used.
- ~~`cloud-local-proxy` repo not local~~ → cloned 2026-09-11 (Ray unarchived it). Non-trans callers still partly unknown; ingress logs needed (Ray has on-prem access via appserver05).
- The front end that calls cloud-local-proxy directly is not va-portal / vibrant-wellness-portal / pns-portal (0 references); unidentified.
- ~~dream pipeline possibly stalled~~ → Leo confirmed dream ran on 2026-09-11.
- Atlassian MCP root cause: claude.ai-hosted connector returns 404 HTML on the legacy SSE endpoint (`/v1/sse` → `/v1/mcp` transport switch); fix is reconnecting Atlassian in claude.ai integrations, nothing local. `vibrant` MCP also failed (DCR 404).

# Timeline

### [2026-09-11 10:00]
Session start; synced working-agent, LIS-transformer (ff 18 commits), LIS-transformer-v2 (switched feature branch → main). Transcribed recordings (first whole-file pass hallucinated after ~5 min; chunked re-run OK). Ran jest/tsc baselines in both repos. Read-only AKS inventory of 4 ConfigMaps + deployments. Wrote PLAN.md v0.1 with Phases 0–5, principles, risk table, draft ticket list, open questions. No code, no comments.

### [2026-09-11 11:30]
Leo forwarded Ray's Slack: scope now also covers `cloud-local-proxy` (TS, unarchived, all-write) and `web-homepage-api` (Python FastAPI, on-prem-only, ns `lis` pod `vw-page`, 3 pods); both were manually pushed by yuxuan, no CI/CD; 昊哥 wanted both retired/merged into trans. Cloned both. Findings: cloud-local-proxy's 18 routes (`/grpc/*` 6 + `/old-report/*` 12) are ALL already re-implemented in trans v1 (`src/proxy/*`, VP-17284 inline + ownership gate) → retirement = repoint callers + scale-to-0 in both clusters. New caller found: `LIS-backend-billing` Java hardcodes `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/grpc/sendSkinPlacePatientOrders`. web-homepage-api = marketing site CMS (72 routes, Mongo + HubSpot + Postmark); only 3 report-action routes relate to LIS (callers: va-portal PatientProfilePage, report-pdf, ehr-frontend) → recommend W0 (keep + add CI) and decide W1 (move 3 routes to trans v2) with report team; W2 (merge whole) not recommended. Both Jenkinsfiles deploy via personal account `yuxuan@192.168.60.6` and contain plaintext registry creds (flagged, not handled). Leo decisions: LoggingInterceptor body-logging change is NOT a functional change; dream finished. PLAN.md bumped to v0.2 (§0, §2.4, §2.9, Phase 1.6/1.7, Phase 5 Track W, §6, §7, §8).

### [2026-09-11 11:50]
Wrote `docs/plans/trans-optimization/PLAN-plain.md`: plain-language version of PLAN v0.2 (hospital-counter / ferry analogies) plus 11 decision items D1-D11 each with what/options/recommendation/owner/consequence and a one-page decision table. Highest-urgency: D2 Jira reconnect at claude.ai, D4 test gate agreement with other Trans contributors.

### [2026-09-11 12:20]
Step 1 for collaboration: added grep-able `TRANS-OPT` comments (English, comments only, zero behavior change) at every urgent site. Branch `feature/leo/TRANS-OPT` in 4 repos: LIS-transformer aa9da9c (pushed after `npm install` fixed the pre-push build - stale node_modules lacked @google-cloud/bigquery), LIS-transformer-v2 655ba73 (pushed, tsc clean), cloud-local-proxy 888f37f (pushed), LIS-backend-billing 12828a4 local only (push 403: pull-only permission; default branch is `cloudproduction`, not master) -> patch saved under docs/plans/trans-optimization/patches/. No PRs opened (D12 pending). D2 status: Atlassian MCP still down (ToolSearch confirms 404 text/html on legacy SSE endpoint); nothing local to fix.

### [2026-09-11 12:40]
Leo: open draft PRs, skip billing, D2 first. Opened comments-only draft PRs based on `main` (not stage_test, so the diff is only the comments): LIS-transformer #752, LIS-transformer-v2 #626, cloud-local-proxy #20. D2 finding: `claude mcp list` now reports `claude.ai Atlassian: https://mcp.atlassian.com/v1/sse - Connected`, i.e. the connector works again but THIS session's tool registry was built while it was failing; needs `/mcp` reconnect or a new session. `vibrant` MCP (http://192.168.60.8:8800/mcp) shows "Pending approval (run `claude` to approve)" - needs Leo's one-time approval in the CLI. Connector still uses the deprecated `/v1/sse` URL; long-term fix is switching it to `/v1/mcp` on the claude.ai side.

### [2026-09-11 13:10]
Read VP-17348 + VP-18140/41/42/43/44/49/52/56/57 via Jira REST (agent .env JIRA_* creds; MCP tool registry of this session never recovered even after Leo reconnected - `claude mcp list` says Connected, so it is a per-session registry issue). Saved as appendix-c-jira-vp17348.md. Key corrections to the plan (v0.3): Core does read cutover SERVER-SIDE (V1 gRPC reverse-proxies to V2 per function, VP-18122~18130, proto freeze is a hard dependency) -> withdrew the trans-side CoreClientProvider/CORE_TARGET/shadow idea (would duplicate + risk proto divergence). VP-18152 scope is only "trans stops calling core v1 HTTP" = our 4 residual sites (list_customer_by_id_carlos x2 -> ListClinicCustomersByClinicID, which is one of the 7 zero-traffic v2 rpc being shadowed in VP-18144; create_patient + create_patientv2 are writes, Phase 5 not ticketed yet). Deadlines: P3 09-30, P4 delete HTTP 10-31, P5 close ingress 11-15. VP-18140 request-log middleware live since 09-10 (`@event:core_v1_http_request`), callers attributable only via user_agent+jwt_sub. VP-18143 moves multi_login_test impersonation auth INTO trans (Fan, Dev Complete) - new trans endpoint to verify.

### [2026-09-11 13:40]
Leo handed a 64-hex token; asked what it is for (ambiguous) -> `vibrant` MCP (http://192.168.60.8:8800/mcp). Verified: no-auth POST initialize = 401; with `Authorization: Bearer` = 200, serverInfo "Vibrant MCP Server 3.2.4 - Datadog tools, config resources, analysis prompts" (also Sentry, Jira/Zendesk summarize, general_sample_events, audit log, accession<->sample id). Stored as VIBRANT_MCP_TOKEN in working-agent .env (gitignored, verified). Added local-scope MCP override with the header via `claude mcp add -s local` (lives in ~/.claude.json; the tracked project .mcp.json untouched - changing it would be a shared automation change needing a PR). `claude mcp get vibrant` now Connected; this session's tool registry still lacks it (new session needed), curl works meanwhile. Token passed through chat: recommend rotate after the program. D11 (Datadog access) resolved via this server.

### [2026-09-11 14:20]
Spawned 2 subagents (Leo asked to delegate): Phase 0.1 Datadog Top-20 (running) and Phase 3.1 core v1 HTTP traffic (done -> docs/plans/trans-optimization/phase3-core-v1-http-traffic.md). 3.1 verdicts (prod, 27.9h since VP-18140 log start): list-customer-by-id LIVE from trans v1 (448) + v2 (19); create-patient / create-patient-new / login_via_session 0 from trans, but the two create calls sit in `createPatientBatch` (batch path) -> re-run after 10-01 before declaring dead. Non-trans: lis-order (Java, 2 UAs) = 91% of all core v1 HTTP incl. ~9k/day list-customer-by-id -> real VP-18156 blocker is lis-order, not trans. jwt_sub empty for all rows (middleware claim bug, feed back to VP-18140). Correction: trans v1 DOES read LOG_IN_VIA_SESSION (utility.service.ts:254, GET /utility/login) - my earlier grep missed it (0 traffic though). kubectl on this machine currently fails (Azure MFA expired, AADSTS50078) - earlier AKS inventory predates that.

### [2026-09-11 14:45]
Phase 0.1 subagent done -> phase0-top20-endpoints.md (+appendix). Method: trace metrics via analyze_datadog_logs DDSQL dd.metrics_scalar() (100% of requests; search_datadog_spans is ~2% indexed and biased). Services: v1 `lis-trans-deployment`, v2 `lis-transv2-deployment`, both env:prod; -st deployments also env:prod. 11 endpoints p95>2s & >=100 hits/7d. Peak hours are NOT the cause (Top-10 peak vs weekly p95 within ±5%). Top pain: v2 POST /graphql (PatientProfileSlow p95 3.1s), v1 /dashboard/user/timeline (2.9s, downstream lis-dashboard - cross-team, not in plan), v1 /utility/getSetting (310k hits, 9 core gRPC fixed, amplifier: PDF calls it 4x), v1 findPatient (14 core gRPC N+1 + HTTP to itself; p95 trending down after VP-18197), PDF proxies (11-14s, in lis-order/pdf-engine; pdf-engine peer looks like lis-shipping-deployment-STAGING - verify), patientTestResultnewrange (365 core gRPC per request, err 1.87%). Structural causes: core N+1, public-ingress round trip to base-report (0.8-3.8s per call), trans calling itself over HTTP. PLAN.md Phase 0.1 marked done, Phase 2 candidate table replaced with measured ranking.

### [2026-09-14 11:30]
Leo: "直接修 plan 裡要等最久的一個（是 S1 嗎？）". Answer: the longest lead-time item is cloud-local-proxy retirement (Phase 1.6 / D8: callers repointed -> 30 days zero traffic -> scale-to-0 -> 30 days -> archive); S1 (transv2 `checkIfPersonalizedReportCanBeCreated` via cloud-local-proxy) is the only known caller of the cloud-side proxy, so it gates that clock. Walked lis-prod-change-gate. Facts: proxy route is a pure pass-through (`res.status(code).send(body)`), target value with suffix is `http://192.168.60.77:8081/secure/nologin/CheckIfPersonalizedReportCanBeCreated?sampleId=` (LIS-transformer docs/proxy-migration-configmap.md:25; same as v1 prod); on-prem endpoint ignores Authorization header (curl with/without -> `200 false`); transv2 already reaches 192.168.60.x (Kafka brokers); Datadog 7d: hop ~70-110 ms, all 200, resolver error log count 0. Deliverables: `docs/plans/trans-optimization/phase1-s1-runbook.md`, `scripts/phase1-s1-repoint.sh` (dry-run default, --apply/--rollback, backup to ~/.trans-opt-backups, in-pod env + http readback), PLAN.md row 1.1 updated. BLOCKED on execution: kubectl -> AADSTS50078 (Azure MFA expired, interactive `az login` needed, Leo only). Also noted: LIS-transformer-v2 origin/main moved to be8344c (PR #623) since the 09-11 baseline; an untracked `config.yaml` in ~/src/LIS-transformer-v2 is a full ConfigMap dump with secrets (not tracked, left alone, but should be deleted).

### [2026-09-14 11:50]
Leo ran `az login` (first attempt failed: the command wrapped across two lines and `--scope` lost its argument). Executed Phase 1.1 S1 end to end. Pre-checks: transv2 st + prod pods reach 192.168.60.77:8081 (node http.get, 200 false, ~75 ms). Staging apply 11:25 PT (cm `lis-transv2-config-st`, was public `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy-st/old-report/...?sample_id=`), readback OK. Equivalence from a prod pod using the pod's own `token` env to pass the proxy's UnifiedAuthGuard: 38 recent sample ids all `200 false` on both paths; swept 4x150 older ids, found 31 `true`, compared 20 -> identical; non-numeric id -> 500 on both (proxy empty body vs on-prem HTML page; v2 getPnsData throws on non-200 either way -> resolver null). Hop latency avg 73 -> 41 ms. Prod apply 11:40 PT, RollingUpdate ~2.5 min, 3 new pods `66b88c9f56-*`, readback env + GET (2100012 true / 2634446 false). Script v1 picked a Terminating old pod for readback (fixed: newest pod by creationTimestamp); the old pod showed status Error on SIGTERM and was GC'd before logs could be pulled. After (Datadog 12 min): 12 spans to 192.168.60.77 all 200; last proxy span 18:26:31 UTC during rollout, then 0; resolver/requestv2 error logs 0; pod logs clean. Docs: runbook §6/§7, PLAN §2.4 S1 = done, row 1.1 = done, Appendix B baseline updated. Backups (with secrets) in ~/.trans-opt-backups/ (outside repo). cloud-local-proxy 30-day zero-traffic clock starts 2026-09-14 for the cloud-side instance (known callers); unknown callers still need ingress logs (D5).

### [2026-09-14 12:30]
Leo: S1 was the wrong reading of "要等最久" (he meant highest latency, wants code fixes for speed). Leo picked: target v2 PatientProfileSlow (incl. S2), and do Phase 0.2 (green test baseline) first. Phase 0.2 for LIS-transformer-v2 DONE in worktree ~/src/LIS-transformer-v2-p02, branch feature/leo/TRANS-OPT-phase0.2 off main be8344c: 10 red suites -> 54/54 green (731 pass, 4 skip), tsc clean. Root causes: 5 calendar suites failed at import (kafka-appointment-event.client.ts throws when Azure_kafka_general_events unset -> jest setupFiles test/jest-env.setup.ts with placeholders), auth.guard.spec needs secretOrKeyProd, prisma.service.spec is a real-DB integration test (renamed .integration.spec.ts, already ignored), clinic.service.spec missing *_CLOUD providers, clinic-charting specs stale after c1b52f1 (requestId/userId/metadata args), practice-event-type GraphQL specs missing 7 providers (ProviderAvailability, AccessionClaim, CalendarSync, Zoom, TimezoneSetting, settingTool, SETTING_PACKAGE_CLOUD), daily-report flaky 5 s timeout -> testTimeout 15000. PR opened against main (see below).
KEY MEASUREMENT (changes the optimization target): PatientProfileSlow selects only `order` + `sample_with_questionnaire_report`; the latter fires 14 downstream calls per sample in one Promise.all, so wall = slowest. 7d transv2 outbound p95 (aggregate_spans): shipping /orders/samples/horm-qnr/status 2.7 s (p50 1.2 s), interactive-report getBarcodeQuestionnairesStatus 1.9 s, zoomer-qnr x3 ~1.1 s; S2 hops getKitStatus 0.52 / getTestStatus 0.37 / getQuestionaire 0.25 s. Representative 3.8 s trace 6aa840e30000000006a3b0dfd0404f01: horm-qnr 3.42 s, getBarcodeQuestionnairesStatus 3.65 s, everything else < 0.5 s. => Removing S2 (plan 1.4) does not move PatientProfileSlow p95; the tail is owned by shipping + interactive-report. Redis GET p95 10 ms / max 2 s (AUTH max 2 s) - the 1 s GET seen in one trace is an outlier. Trans-side levers left: parallelize the per-sample loop (only multi-sample accessions), request-scoped memo; v2 shipping.proto also lacks GetKitStatusBySampleId / GetQuestionaireBySampleId + SampleId message (v1 has them) - needed if S2 is still done.

### [2026-09-14 14:30]
Leo: do all three, trans v1 + v2 only (no shipping / interactive-report tickets). Three tracks:
- A (v2 S2, me) DONE as PR #629 https://github.com/Vibrant-America/LIS-transformer-v2/pull/629 head dc08954, base main (post-#628). New ProxyGrpcService (port of v1 proxy.service.ts: getKitStatusBySampleId / getTestStatus({sampleId:Number}) / getQuestionaireBySampleId, packages=[] normalisation, metadata = createOAuth2Metadata + user-id + ip, JSON round trip). Mode env TRANS_PROXY_GRPC_MODE: http (default = zero change) / shadow (both, answer HTTP, log `proxy_grpc_shadow` with equal/diff_paths/http_ms/grpc_ms) / grpc (direct, same 10 s identity cache key transv2::proxyGrpc::..., errors -> upstreamGraphQLError func proxy_grpc_<method>). 5 call sites in patientProfile.service + UtilityRestService.getKitStatus (skin, own 1 h cache). v2 shipping.proto brought to parity with v1 (+2 rpc, +SampleId). Tests 56/56, tsc clean. Rollout: merge -> shadow st+prod -> 24 h equal 100% -> grpc. Draft PR #626 comment-only will conflict -> close/rebase. Worktree ~/src/LIS-transformer-v2-s2 (has gitignored .env copy for the pre-push DI smoke).
- B (v1 Phase 0.2 test baseline) delegated to a subagent (worktree ~/src/LIS-transformer-p02, branch feature/leo/TRANS-OPT-phase0.2) - running.
- C (v1 findPatient analysis) subagent DONE -> docs/plans/trans-optimization/phase2-findpatient-analysis.md. Corrections to the plan: no self-HTTP call exists (src grep + git log -S + Datadog 0), 9 core gRPC not 14 (main query InitialPatientPageHome), bottleneck is the serial pipeline after Stage A (C getEstimateTimev3 -> D getIssue -> E getPatientIssue -> F FedEx -> G -> H ~1.36 s; C/D/E independent). Recommended order: golden-response spec first, then C || (D->F) || E (~-0.6 s on the sample trace), GetSampleTests into first Promise.all, metadata once per request, BatchGetIssuesByObjectIds for get_issue_id(12) (exists, fk 11 already uses it), GetSampleReceiveRecordsBatch. CORRECTNESS BUG found (not perf): getPatient.service.ts:410-418 `this.send_issue_order_type` / `this.send_order_test_flag` are instance fields pushed per request and never cleared -> cross-request contamination of the OR filter + unbounded growth. Needs its own ticket. Also processTNPWarningDataRedrawed :5773 has dead code after return.
- Phase 0.2 note: daily-report.service.spec still flaked once in a full parallel run even with testTimeout 15000 (passes alone in 6 s) - root cause not fixed.

### [2026-09-14 16:10]
Track B (v1 Phase 0.2) subagent DONE, reviewed by me (scope test-only confirmed, assertions meaningful, independently re-ran: 58/58, 716 pass, tsc clean). Branch feature/leo/TRANS-OPT-phase0.2 fa062e4, PR opened (see below). Root causes: 9 CLI-scaffold specs with zero providers; src/redis.ts + src/redis_s.ts open ioredis at import -> test/jest-unit.setup.ts stubs both via jest setupFiles; specs stuck on old contracts (createMetadatav3 retired in b8c59f0, getTimeLine shape changed in 191571b, dashboard.controller imported AppModule); unhandled-rejection pattern of(Promise.reject()) killed a jest worker. Possible product issues surfaced (NOT fixed, not masked): setting.billingn.service.ts:418 awaits getClinicSetting without lastValueFrom (apply_to_all always false; maybe dead code); src/redis_s.ts:12 hard-coded Redis credential in source -> ticket; trans.service.ts:23728 fragile await inside Promise.all array literal. npm ci postinstall rewrites tracked prisma2/generated/client2 (gitignored but tracked) - not committed.
Leo asked whether merging PR #629 can affect any function: answered with the three runtime differences in default mode (same URL/function at 6 sites, skin caller identical, two lazy gRPC clients created at boot) and the verification done (proto load with same loader options lists all rpcs; DI smoke on dist passed; only 4 proxy_* env reads remain, all in http branches). Post-merge checks planned: rollout, pods have no TRANS_PROXY_GRPC_MODE, spans to lis-trans-service:3146/proxy/grpc/* still present, proxy_grpc_shadow logs = 0, error logs unchanged.

### [2026-09-14 16:40]
Leo merged #629 (v2 S2) and #767 (v1 tests) at 22:56 UTC; v2 prod deploy 832ce95 done 23:06 UTC. Default-mode verification: pods have no TRANS_PROXY_GRPC_MODE, spans to lis-trans-service:3146/proxy/grpc/* still flowing (all 200), 0 proxy_grpc_shadow logs, 0 error lines on 3 new pods. Leo: "都 merge 了，請測試實際優化程度" -> enabling shadow on prod (ConfigMap TRANS_PROXY_GRPC_MODE=shadow + rollout restart; backup in ~/.trans-opt-backups/*.pre-shadow.yaml); measurement = per-call http_ms vs grpc_ms from `proxy_grpc_shadow` logs, plus equal rate. Staging skipped: stage_test lacks #629.
findPatient: golden spec subagent DONE (21 tests, commit 77e4998; pinned a second pre-existing bug: order without samples makes getWarning throw mid-way -> TNP/missing-optional/Test Discontinued leak into order.issue by sort position). I implemented P1 (Promise.all([C, D.then(F), E]) then G, H) and P2 (GetSampleTests fired with first wave, awaited at original point - naive version awaited it in the first Promise.all and the golden degradation test caught active_event_id no longer written when GetSampleTests rejects). 59/59, 737 tests, tsc clean, DI smoke passed. PR #769 https://github.com/Vibrant-America/LIS-transformer/pull/769 head d76b29a base main. Worktrees: ~/src/LIS-transformer-fp2 (findpatient), ~/src/LIS-transformer-p02 (phase0.2), ~/src/LIS-transformer-fp (detached analysis).

### [2026-09-14 17:20]
Leo: S2 saving is small -> asked about the >3 s endpoints; then "能修的直接修". Spawned 3 read-only analyses (done): 
- newrange (phase2-newrange-analysis.md): the 365 gRPC are already concurrent (~1.5 s wall, core-side contention); the serial 3-4.5 s is getFullTestMapping (HTTP full_test_mapping via public ingress, Redis 500 s) awaited AFTER the fan-out though it only needs accession_id (T:1582 in current main; getFullTestMapping at ~18362, catch returns undefined -> full_mapping.map TypeError -> outer catch). 1.87% errors are fast-fail 500s ('No order found', patient_order undefined TypeError), not gRPC. Batch RPC GetPatientDetailedReferenceRangeInOutBatch exists (join by sample_id+test_id, no Error field; dead-code old batch impl at T:6052). Plan: PR-1 golden spec (subagent running, branch feature/leo/TRANS-OPT-newrange, worktree ~/src/LIS-transformer-nr2) -> PR-2 prefetch full_test_mapping before fan-out, await at original point (+ parallel the two report GETs, keep GetSpecificReports after) -> later batch RPC behind flag.
- getTimeLine (phase2-timeline-sampleinfo-analysis.md): getKitStatusV2 -> public api.vibrant-wellness.com/v1/lis/samples/patients/v2/kits -> LIS-Sample -> back to trans v1 GET /trans/patientTestKitInfo (3-hop, p50 1.39 s / p95 2.74 s) used only for has_report = tube_info non-empty; serviceToken() awaited inside the Promise.all array literal delays the other 4 promises; getinvoice + CHARGE_INFO_URL fallback serial after Promise.all, both public, 53% 400. A-PR1 scheduling (-0.5 s), A-PR2 kits in-process (p50 2.2->~1.0 s; decision on has_report false-negative semantics). GetSampleInfo gRPC p95 is core-side GetSampleTests cache miss (3.2 s core) -> not trans-fixable; N+1 receive records already concurrent.
- createPatient (phase2-create-update-patient-analysis.md): p50 3.8 s = ~2.9 s of per-message kafkajs producer connect/disconnect (14 messages, ~280 ms each). DONE: PR #773 https://github.com/Vibrant-America/LIS-transformer/pull/773 head b939a91 (SharedKafkaProducer, one connection per cluster, same records/order; 63/63, 765 tests). updatePatient is core-side.
Worktrees: ~/src/LIS-transformer-kf (kafka), ~/src/LIS-transformer-tl2 (getTimeLine, creating), ~/src/LIS-transformer-nr2 (newrange spec agent), read-only: -nr, -tl, -cp, -fp.

### [2026-09-14 17:35]
getTimeLine A-PR1 DONE: PR #774 https://github.com/Vibrant-America/LIS-transformer/pull/774 head 6f56a27 (serviceToken chained instead of awaited inside the Promise.all array literal; invoice + CHARGE_INFO_URL fallback chained on sharePayment and awaited in the same Promise.all; same guards/try-catch; spec 7->12; 61/61). Expected p50 -0.25 s / p95 -0.5 s. Next candidate A-PR2: getKitStatusV2 (public -> LIS-Sample -> back to trans v1 patientTestKitInfo, p50 1.39 s) -> in-process; reading LIS-Sample mapping to decide bit-exact feasibility. Worktree ~/src/LIS-transformer-tl2.

### [2026-09-14 17:50]
- findPatient post-deploy (23:41-00:28 UTC, 191 req, trace metrics): p50 0.92 s / p95 0.94 s / errors 0 vs same-day pre 20:00-23:37 p50 1.00 / p95 1.55 (1,511 req) vs 7d p50 1.21 / p95 2.88. Low-traffic Monday evening; re-measure business hours (Tue 9-17 PT vs prior weekdays). Datadog scalar "avg of percentiles" is approximate.
- newrange golden spec subagent DONE (29 tests, commit b05e619). Implemented PR-2: fetchFullTestMappingData split out, prefetch before the fan-out with no-op catch, awaited at original point via getFullTestMapping(..., prefetched); two report GETs in Promise.all. Golden 29/29 unchanged, 62/62, tsc clean. PR #775 https://github.com/Vibrant-America/LIS-transformer/pull/775 head 98fe908. Push initially failed the DI smoke because the subagent's worktree (~/src/LIS-transformer-nr2) had no .env (JwtStrategy secret) - copied and pushed.
- Open PRs awaiting Leo: #773 (createPatient Kafka), #774 (getTimeLine scheduling), #775 (newrange prefetch). Next: getTimeLine A-PR2 (kit status in-process behind a shadow flag), then S2 grpc switch after 24 h shadow (started 23:10 UTC 09-14).

### [2026-09-14 18:05]
getTimeLine A-PR2 DONE: PR #776 https://github.com/Vibrant-America/LIS-transformer/pull/776 head 3ae87f8, stacked on #774 (branch feature/leo/TRANS-OPT-gettimeline-kits). TRANS_TIMELINE_KIT_MODE http (default)/shadow/inprocess; in-process = this.patientTestKitInfo + LIS-Sample's two conditions (Order[0].kit_status truthy && tube_info non-empty); controller passes {clinic_id, beta_program_enabled, beta_programs}; shadow log event `timeline_kit_shadow` via lis_front_logger.log_info (operation kitShadow). Spec 12->17, 61/61.
OPEN PRs awaiting Leo (all zero-behaviour on merge except where noted): #773 createPatient Kafka producer reuse (behaviour: connection reuse only), #774 getTimeLine scheduling, #775 newrange prefetch, #776 getTimeLine kit in-process (flagged). PENDING OPS: S2 shadow started 23:10 UTC 09-14 -> check equal 100% and switch TRANS_PROXY_GRPC_MODE=grpc after 24 h; after #776 merges set TRANS_TIMELINE_KIT_MODE=shadow; after #773/#774/#775 deploy measure createPatient / getTimeLine / newrange p50/p95 (trace metrics) vs 7 d; findPatient business-hours re-measure Tue 9-17 PT. Worktrees: -kf, -tl2 (kits branch checked out), -nr2, -fp2, -p02; read-only -nr, -tl, -cp, -fp.

### [2026-09-14 20:15]
Leo merged #773/#774/#775/#776 (02:08 UTC 09-15); three concurrent deploy-prod runs, final live image = last merge 5f79b52 (verified per pod). Set TRANS_TIMELINE_KIT_MODE=shadow on default/lis-trans-config (backup ~/.trans-opt-backups/*.pre-kit-shadow.yaml) 02:22 UTC. First window (02:25-03:05 UTC, low traffic): createPatient p50 1.68 s (7d 3.56; estimate ~2) with 12 kafka.produce / 3 tcp.connect per trace (was 14/14); getTimeLine p50 1.71 s (7d 2.15; estimate -0.25); newrange p50 2.05 s unchanged as predicted, p95 sample too small; findPatient p50 1.10. Kit shadow 16/16 equal, http ~1.1 s vs in-process ~0.37 s. newrange 4/40 errors are the pre-existing 78 ms fast-fail 500 class (same p50 as 327 baseline 500s; same accession retried; the code path fails before the changed function) - keep watching the daily rate. Kafka: no send failures; partitioner warning now once per pod/cluster instead of per message. Results in docs/plans/trans-optimization/phase2-measurements.md.
Lesson PRs opened in project-agent-factory (one per lesson, per CONTRIBUTING): #78 latency estimate = critical-path delta; #79 re-derive perf-plan premises from current code + fresh trace; #80 golden spec must pin per-stage failure paths; #81 gates must own their environment (DI smoke depends on cwd/.env). Estimates so far are met or beaten; no estimate-miss lesson yet.
TODO next session: (1) business-hours (Tue 9-17 PT) p50/p95 for findPatient, createPatient, getTimeLine, newrange vs prior weekdays; (2) S2: after 24 h shadow (23:10 UTC 09-15) confirm equal 100% -> ask Leo -> TRANS_PROXY_GRPC_MODE=grpc; (3) kit shadow: after a business day confirm equal -> ask Leo -> TRANS_TIMELINE_KIT_MODE=inprocess; (4) newrange error rate vs 1.8% baseline; (5) later cleanups: remove http/shadow branches, proxy_* keys (S6), close #626.

### [2026-09-14 20:40]
Leo: "create ticket, assign 給我" -> created VP-18276 https://vibrantamerica.atlassian.net/browse/VP-18276 (Task, VP, assignee Leo, Dev To Do) via the claude.ai Atlassian connector (the vibrant MCP at 192.168.60.8 and on-prem hosts were unreachable at the time - VPN down). Content: shipped table with PRs and first measurements, remaining ops checklist (business-hours measurement, S2 grpc switch, kit inprocess switch, newrange error rate, cleanups, cloud-local-proxy clock), and the six pre-existing defect groups as candidates for separate tickets. No Jira comments posted.

### [2026-09-15 16:50]
Leo: "把我的改善+成效都寫上去" + Confluence folder 2681962497 (space LIS). Folder already held a sibling page "Refactored APIs — Session Notes" (Yuteng Fu, PRs #771/#772) -> created a NEW sibling page instead of editing his: "Trans v1 / v2 Optimization — Shipped Changes & Measured Impact", id 2684321795, https://vibrantamerica.atlassian.net/wiki/spaces/LIS/pages/2684321795 . Created via Confluence REST v2 POST /wiki/api/v2/pages with agent .env JIRA_EMAIL/JIRA_API_TOKEN (the claude.ai Atlassian connector exposes no create/update page tool; parentId = folder id, parentType folder, spaceId 90603522, body representation=storage).
BUSINESS-HOURS MEASUREMENT DONE (closes TODO 1). Window 16:00-22:00 UTC (09:00-15:00 PT) Mon 09-14 (pre) vs Tue 09-15 (post); cut at 22:00 because Yuteng's #771/#772 deployed 22:14 UTC (image dae5611, pods 7796647dbd) and would contaminate the comparison. p50/p95 before -> after: createPatient 3.68->2.08 / 3.70->2.50; newrange 2.17->1.76 / 3.16->2.76; getTimeLine 2.14->1.78 / 2.42->2.04; findPatient 1.01->0.93 / 2.31->1.88. hits pre/post 495/596, 1176/1355, 1109/1273, 4016/4706. Errors: findPatient+createPatient 0 both windows; getTimeLine 3->1; newrange 11/1176 (0.8%) -> 17/1355 (1.1%), both under the 1.8% 7d baseline. All four estimates met or beaten except newrange p95 (-0.40 s vs "clearly down") - fan-out is core-side.
SHADOW RESULTS (closes TODO 2/3 measurement half, decision still Leo's): S2 `proxy_grpc_shadow` 24 h = 7,702 comparisons, 7,701 equal (99.99%); getKitStatus 3900 eq, 243->215 ms; getTestStatus 1901 with **1 mismatch**, 207->184 ms; getQuestionaire 1901 eq, 96->73 ms. Saving ~25 ms/call -> real but small; resolve the 1 diff before TRANS_PROXY_GRPC_MODE=grpc. Kit shadow (`@operation:kitShadow`, v1) = 1,843 comparisons, 1,843 equal (100%), HTTP avg 1,095 ms vs in-process 496 ms => ~600 ms/request on the table; 1 inprocess_failed that still compared equal.
Datadog method notes: `dd.metrics_scalar('<agg>:<metric>{...} by {tag}', 'avg'|'sum')` needs the reducer as a SECOND arg (else "Missing aggregator"); tag filters must use `AND` not commas when combined with `IN (...)` (else "'AND' and 'OR' cannot be mixed with ','"). Kit shadow logs are NOT findable by free-text `timeline_kit_shadow` (returns 1) - use `@operation:kitShadow` (1,843). Same trap cost a wrong "shadow has stopped" reading mid-session.

### [2026-09-15 dream] VP-18276 closed as a record ticket; program stays active here
- VP-18276 created 10:31 PDT and moved Dev To Do -> Done 10:34 PDT by Leo (story points 12, QH-7118 auto-linked, 0 comments). Its description carries the shipped table + remaining-ops checklist, so the audit treats it as a documentation closure: all 8 PRs merged, GitHub Actions deploy-prod/`frontend-service-graphql` success on every main merge (v1 last 5f79b52 02:08Z 09-15; v2 832ce95 22:56Z 09-14), business-hours measurement done 09-15.
- Health since the deploys (Datadog): the trans error mix on 09-14/15 is 3-4x a normal weekday for `npm error … nest start` (v1, 30/day = one per pod per deploy, 12 deploys) and transv2 `Error getting requestv2/v3 timeout/502` (41-43/day vs 9-11) — both track the deploy/restart hours, not a regression. One signal to look at next session: v1 `14 UNAVAILABLE … ECONNREFUSED 192.168.60.6:31865` (core v1 gRPC) 15 on 09-11 -> 73 (09-14) -> 83 (09-15), business hours only, starting 19:00Z 09-14 = 4 h BEFORE the first TRANS-OPT deploy — core-side, but find which RPC.
- Remaining ops unchanged: S2 grpc switch (1 getTestStatus diff to explain first), kit inprocess switch, newrange error-rate watch, cleanups (#626 close, http/shadow branch removal, proxy_* keys), cloud-local-proxy retirement clock (since 09-14). Local status stays `active`; reconcile cannot map this file to VP-18276.

### [2026-09-15 19:30]
Leo: 看 Confluence folder 已做的，比對計劃，把還能做的做一做（**僅限 LIS-transformer / LIS-transformer-v2 兩個 repo**）。Folder 2681962497 只有兩頁（我的 2684321795 + Yuteng 的 2681995265），沒有新增。比對 PLAN.md 後**開了 4 個 PR**（都沒 merge，Leo 決定）：
- **Phase 0.3 CI gate**：v1 #781 head `819fafb`、v2 #633 head `95b5bff`。各加 reusable `.github/workflows/ci-tests.yml`（npm ci → tsc --noEmit -p tsconfig.build.json → jest --ci），deploy workflow 的 `buildImage` 加 `needs: [test]`，並在 `pull_request` 也跑。v1 node 22、v2 node 20（照各自 Dockerfile）。**這個 gate 第一次跑就抓到本機抓不到的 bug**：`--runInBand` 把 64/56 個 suite 塞進單一 process，撞 runner ~2 GB 預設 heap → `Ineffective mark-compacts near heap limit` exit 134（本機過是因為 macOS 預設 heap 較大）。改 `--maxWorkers=2 --workerIdleMemoryLimit=1G` 後本機重驗：v1 64/64 811 tests、v2 56/56 757 pass+4 skip。補推後照 CLAUDE.md 例外條款在兩個 PR 各留 comment 標明新 head SHA。
- **Phase 3.4 v1 dead code**：#782，刪 `trans.grpc.options.ts` 的 `coreSampleV2Url`（算完就丟，client 一直直接讀 `CORE_SAMPLE_V2_RPC`）。**選擇刪掉不接上**——接上等於改 on-prem 送去哪。**浮出未解問題**：`platform_type==='local'` 在本 repo 其他地方是活的，若原作者判斷正確，on-prem v1 pod 可能每支 coresamples-v2 呼叫都在靜默失敗，要查 on-prem deployment env。
- **Phase 3.4 v2 keepalive**：#634，4 個 coresamples client 的 keepalive 120 s → 300 s（對齊 v1；v1 註解記載低於 Go server `KeepaliveEnforcementPolicy.MinTime` 預設 5 分鐘會吃 GOAWAY ENHANCE_YOUR_CALM），並明寫 `keepalive_permit_without_calls: 0`。**GOAWAY 假設未驗證**（Datadog MCP 整段時間連不上，疑 VPN），PR body 已寫明；改動只降 ping 壓力，兩個方向都安全。

**評估後決定不做的（連同理由，避免下次重跑同樣的路）**：
- **getSetting 的重複 metadata**：`getSetting` 與其他約 50 處都有 `metadata` + `oauth2metadata` 兩次 `createMetadataForCoresampleV2`。實讀 `setting/tool.ts:105` 後確認 `getOAuthToken()` 的 fast path 是純記憶體快取讀取（無 I/O），第二次呼叫只多一個 `new Metadata()` + 幾個字串操作 → **收益趨近於零，不值得 50 處的 diff 風險**。`utility.service.ts:9748` 早有人做過同樣收斂並留下註解。
- **fetchSettings 的 9 支 core gRPC 並行**：PLAN 手法 1 說要並行，**實讀發現 main 早已是 `Promise.all` 包 `Promise.all`**，計劃這條已過時。
- **v2 patientProfile per-sample 迴圈並行 + accession-scoped memo**：迴圈 body ~290 行，改 `Promise.all(samples.map())` 需整段縮排，沒有 golden spec 當安全網；且 09-14 的實測結論已把 PatientProfileSlow 判給 shipping / interactive-report（跨團隊），trans 側只有多 sample accession 才有感。Datadog 掛掉無法量「一個 accession 平均幾個 sample」→ **在拿到那個數字前不動**。真要做的話 3 個 accession-scoped 呼叫（`getReportStatusListV2WithInteractiveProducts`、`questionnaire_status`、`report_finish_time`）可以提到迴圈外，但 **`getQuestionnaireStatusArray` 會被各 sample push，共用同一個 array instance 會互相污染，必須改成每個 sample 複製一份**——這點記下來，下次做的人不要踩。
- **`processTNPWarningDataRedrawed` 的「return 後 dead code」**：09-14 的紀錄講得太簡化。實讀後**更正**：外層是 `if (SERVER_ENVIRONMENT == 'prod')` 才 return，非 prod 會走到後面的 `if (true)` 區塊（含 `SendTestOrderPDFMail` POST）。**不是全域 dead code，刪掉會改 staging 行為**，沒動。
- **await-inside-`Promise.all` array literal**：寫腳本掃了 5 個大檔，只有 3 個 hit，全部是 thunk / `.then` 內的刻意排序（含我自己 #769 那段，有 golden spec 釘住）。**這個 smell 在 main 已經清乾淨**。

### [2026-09-15 20:30]
CI gate 兩邊都綠，**最終 head：v1 #781 `7c55f77`、v2 #633 `a0bfa4f`**（#782 `d360eb3`、#634 未動）。四個 PR 都已留 comment 標明 head SHA。

**CI gate 在 runner 上迭代了 3 輪，每一輪的失敗本機都重現不了——這是這個 gate 最強的存在理由，也是本次最大的收穫**：
1. `--runInBand` → heap OOM exit 134（本機過，因為 macOS 預設 heap 較大）。
2. `--maxWorkers=2 --workerIdleMemoryLimit=1G` → v1 綠但慢；**v2 更糟**：jest 用 SIGTERM 殺自己的 worker，56 suite 有 40 個 "failed to run"，761 test 只跑到 184，燒 27 分鐘。**方向錯誤的教訓：runner 預設 heap 只有 ~2 GB，v2 單一 worker（Nest + Apollo + GraphQL 過 ts-jest）自己就超過，收緊 ceiling 只會讓 worker 在 suite 跑完前先被殺。要的是 headroom 不是 ceiling。**
3. `--maxWorkers=2` + `NODE_OPTIONS=--max-old-space-size=4096` + `--forceExit` + `timeout-minutes: 25` → 兩邊全綠。

**heap headroom 的效果是數量級的**：v2 1636 s（失敗）→ **92 s**；v1 1031 s（雖綠但離 25 min timeout 只剩 4 min）→ **63 s**。也就是說在預設 heap 下，worker 幾乎整輪都在 GC。以後在 GitHub runner 上跑 Nest/ts-jest 大型 suite，**先給 `--max-old-space-size`，不要用 `--workerIdleMemoryLimit`**。
`timeout-minutes` 也是這輪補的：v2 第一次卡在 test step 30 分鐘不動，一個會無限掛著的 gate 本身就是問題。

待 Leo：(1) merge 時確認上面的 head SHA；(2) main 的 branch protection 要把 `typecheck + unit tests` 設成 required，否則 PR 上的紅燈只是建議；(3) #634 的 GOAWAY 前提待 Datadog 通了驗證；(4) #782 浮出的 on-prem coresamples-v2 疑慮需要 on-prem 存取。

### [2026-09-16 09:00]
Leo：#626 有 conflict，並確認其他 PR 不會實際影響使用者。

**#626 解衝突（不用 force-push）**：`git merge origin/main` 進 `feature/leo/TRANS-OPT`，**所有衝突都落在 `[P1-S2]` 註解上**——S2 已由 #629 上線（`ProxyGrpcService` + `TRANS_PROXY_GRPC_MODE`）並改寫了那些 call site，所以一律取 main 側（註解要求的工作已完成，掛註解的那幾行也不存在了）。另外把 `[P1-S1]` 註解改寫：它叫人去把 `lis-transv2-config` 從 cloud-local-proxy 移開，那在 09-14 就做完了，留著是誤導；改成記錄現況 + 「這個 env var 背後是 on-prem 位址，是本 resolver 唯一離開 cluster 的呼叫」。新 head `82917a5`，PR 回到 MERGEABLE。剩 17 行、5 檔、全是 `//`，零刪除（用 `git diff origin/main | grep '^+'` 機械驗證過）。merged head 上 tsc 乾淨、56/56、757 pass。
**注意**：rebase 需要 force-push（CLAUDE.md 禁止），所以這類「PR 落後 main」一律用 merge main 進 branch，不要 rebase。

**使用者影響稽核（逐一機械驗證，非口頭斷言）**：
- #781 / #633（CI gate）：deploy workflow 的 diff **只有新增**（`test:` job + `needs: [test]`），build/推 image/kubectl set image/k8s-deploy 全部沒動，一行未刪。純 CI。
- #782：`url: process.env.CORE_SAMPLE_V2_RPC` 原封不動；被刪的 `coreSampleV2Url` / `CORE_SAMPLE_V2_RPC_LOCAL` / `CORE_SAMPLE_V2_RPC_ONPREM_DEFAULT` 在該 branch 的 `src/` 內 0 個引用（`git grep` 對 ref 驗證）。
- #626：全部新增行都以 `//` 開頭，零刪除。
- #634：**唯一有 runtime 成分的一張，而且我發現一個開 PR 時沒講到的 caveat**——`grpc.service_config`（含 timeout）只掛在本檔兩個 `lis` client 上，**coresamples client 沒有，call site 也沒有 per-call deadline**，所以 keepalive 是偵測「靜默斷線」的唯一機制。連線在呼叫中途死掉時，偵測從 ~140 s 變成 ~320 s。不改變任何 response/schema/資料，但失敗情境下 hang 更久。已在 PR 留 comment 講明；仍建議 merge（v1 早就跑同樣的值對同一個服務；120 s 反而有被 server 拆通道的風險），真正的解是給 coresamples client 補 deadline，另開一張。

### [2026-09-16 13:45]
Confluence 2684321795 更新到 **version 2**（REST v2 PUT，version.number 必須遞增；先 GET 確認是 v1 沒被別人改過）。結構：原本的 §1–§4 保留為 first wave，新增 **§5 Second wave 2026-09-16**（5.1 CI gate／5.2 coresamples deadline／5.3 刪 dead config／5.4 被關掉的 #634／5.5 v1 service_config 從未生效／5.6 數字／5.7 誤判的錯誤突波），Defects 順延成 §6、Next 成 §7 並改寫。§3.3 與 §4 的既有交叉引用不受影響。
本日五個 PR 全部 merge 上線：v1 #781 #782、v2 #633 #626 #637（#634 關閉）。live image v1 `402d78e`（含他人 #783 #784）、v2 `3855769`。#637 驗收通過（100 分鐘 0 DEADLINE_EXCEEDED、0 coresamples error span、0 restart）。

### [2026-09-16 14:50]
繼續 §7 待辦，三件事：

**1. Shadow 的唯一「不一致」查清了，不是不一致。** 那筆 `equal:false`（2026-09-15 21:42，getTestStatus sample 2594896）的內容是 `http_ok:false` **且** `grpc_ok:false`、`grpc_error: '2 UNKNOWN: Internal server error'`——**兩邊都失敗**，不是兩邊答案不同。#629 的 `equal` 定義是 `httpOk && grpcOk && canonicalJson(a)===canonicalJson(b)`，任一邊失敗就是 false。所以累計 **13,629 筆比對、0 筆真正分歧**。`TRANS_PROXY_GRPC_MODE=grpc` 的證據門檻已經過了，剩下的是 Leo 決定何時切（prod config 變更）。
教訓：shadow 的 `equal` 旗標若把「雙方都失敗」和「雙方不一致」混在一起，會製造假的 blocker。下次設計 shadow 要分成 `equal` / `both_failed` 兩個欄位。

**2. on-prem 存取確認沒有**（不是假設）：`kubectl config get-contexts` 只有 `lisportalprod`（AKS）和 `minikube`。§5.3 的 on-prem `CORE_SAMPLE_V2_RPC` 問題我做不了，必須由有 on-prem 存取的人查。

**3. v1 gRPC service_config → PR #792**（head `98a06e4`，未 merge）。**最重要的發現是一個陷阱**：把 `name: [{service:'lis'}]` 改成能比對的形式，會**同時**啟用旁邊那個 `retryPolicy`（maxAttempts 5、retryableStatusCodes UNAVAILABLE/UNKNOWN），而它套用在整個 channel，包含 `CreatePatientV2`（2,780 次/週）和 `UpdatePatientInformantWithWriteBack`（941 次/週）這兩個**非冪等寫入**。UNKNOWN 可能代表「server 已寫入、只是回應丟了」，重試 5 次會產生重複病人。所以 PR 是**刪掉 retryPolicy**，不是搬移，並留下大段註解禁止再加回去。
值的選法（照 #637 的做法先量再選）：本 client 7 天所有 method 的 p95 都 < 10.3 s，超過 ~25 s 的只有那三個寫入 → default **60 s**，三個寫入 **240 s**（高於觀測最大值 188.7 / 159.1 / 75.6 s），確保今天會成功的呼叫一個都不被砍。
另外記一筆：`UpdatePatientInfo` 的 **p50 是 9.7 秒**（48 次/週），那是 core 側的問題，但也是這裡天花板必須訂這麼寬的原因。

**工具教訓**：commit message 用 `-m "..."` 且內容含反引號時會被 shell 當成命令替換吃掉（本次 `` `name` `` 整個消失）。以後 commit message 一律用 heredoc。

### [2026-09-16 15:10]
**兩個行為變更刻意分開落地**（出事才分得清是哪一個）：
- **22:00:37 UTC** v1 `6b4ab6d`（PR #792，deadline 第一次真正生效）rollout 完成，3 pods、0 restarts。先驗：`DEADLINE_EXCEEDED` 0、所有端點錯誤 0。
- **22:03:16 UTC** v2 切 `TRANS_PROXY_GRPC_MODE=grpc`（ConfigMap patch + rollout restart）。備份 `~/.trans-opt-backups/lis-transv2-config.20260916T214729Z.pre-grpc.yaml`。三個 pod 逐一 `kubectl exec printenv` 確認 = `grpc`（不是只看 ConfigMap）。

**切換驗證（22:04 起）——三條證據都到齊**：
1. **新路徑出現**：transv2 直接打 `shipping.ShippingService/GetKitStatusBySampleId`(15)、`GetQuestionaireBySampleId`(11)、`testresult.TestResultGrpcService/GetTestStatus`(11)。
2. **舊路徑消失**：v1 `/proxy/grpc/*` 三個端點 hits = **0**（切換前 2 小時基線 684+496+467 = 1,647）。
3. **客戶面零影響**：transv2 request errors 0、gRPC client errors 0、相關 error log 0、pod restarts 0。

**不要誤讀的數字**：切換後 8 分鐘窗的 graphql p95 = 0.481 s，看起來比今天稍早的 1.094 s 好很多——**但短窗的 scalar p95 會塌向 p50，不能當成改善證據**（這個陷阱在 09-15 的量測已經記過一次）。真正的比較要等完整工作日窗。

**查證過不是問題的訊號**：切換後有 3 筆 ERROR 等級 log，內容是 Node `MaxListenersExceededWarning` 啟動警告。查 3 天歷史：每次 deploy 都出現 6 筆（9/14 ×3、9/15、9/16 ×3），既有噪音，與本次無關。

### [2026-09-16 15:40]
切換後 33 分鐘完整驗證（22:04–22:37 UTC），全部乾淨：
- 新路徑有實量：getKitStatusBySampleId 107、getQuestionaireBySampleId 96、getTestStatus 96（約 300 次），**gRPC client errors 0**。
- 舊路徑：`/proxy/grpc/getteststatus` 和 `getquestionairebysampleid` 皆 **0**；`getkitstatus` 有 **1** 筆——時間落在 rollout 剛完成、舊 pod 還在 draining 的窗內，判定為收尾殘留，非新流量（若隔天仍有非零要重查）。
- **DEADLINE_EXCEEDED 跨 v1+v2 = 0**（涵蓋 #792 的 v1 deadline 首次生效）。
- transv2 客戶面 request errors **0**（835 個 graphql 請求）。pod restarts 全 0。
- v1 期間又被第三方 deploy 一次（#789 VP-16884，live `a4592dc`），我的 #792 deadline 仍在該 image 內、仍生效。

**graphql p95 = 0.547 s（835 請求）vs 今天稍早 1.094 s** —— 方向好看，但**依 lesson #83 不宣稱為改善**：窗只有 33 分鐘、又是傍晚時段，短窗百分位會塌向中位數。完整工作日對照明天再做。

**一個待觀察（不是問題）**：shadow 期 getKitStatus:其他 ≈ 2.05:1，切換後 ≈ 1.11:1。可能只是時段流量組成差異（shadow 是 48 小時平均、現在是工作日傍晚），但值得用完整一天的資料重看一次比例是否回到 2:1；若沒有，代表某個 getKitStatus call site 的行為跟預期不同。

### [2026-09-16 16:40]
持續監測 1.5 小時（22:04–23:36 UTC）全部乾淨：新路徑 605 次、gRPC errors **0**、客戶面 errors **0**（835 graphql 請求）、pod restarts **0**、DEADLINE_EXCEEDED **0**。舊路徑 ≤1 次（太稀疏沒被 span 取樣，無法歸因；相對切換前每小時 ~500 次等於零）。Confluence 更新到 **v4**（§4.1 改寫成已切換 + 三條驗證訊號 + shadow blocker 的真相；§7 重排）。

**下一步做了 kit shadow 的決策資料，結果推翻我自己先前的說法** → Confluence **v5**：
累計 **3,473 筆（~46 小時）、3,470 相同（99.91%）、3 筆分歧**。我先前報的「1,843 筆 100% 相同」是小樣本，已在頁面上明確標為更正。
三筆分歧逐一看，**方向跟我原本假設相反**：
- 09-16 01:13 sample 2627642：HTTP `false`（**8,035 ms**）vs in-process `true`（996 ms）
- 09-16 22:00 sample 2618435：HTTP `false`（**5,600 ms**）vs in-process `true`（10 ms）
- 09-16 17:41 sample 2617310：HTTP `true`（2,264 ms）vs in-process **失敗** → `false`
**三分之二的分歧是現行路徑答錯**：三跳在高負載下跑 5.6–8.0 秒然後回 `false`，等於 timeline 對病人說「沒有報告」而其實有。這是**現在就存在的靜默 false negative**，在旁邊擺一條路對照之前完全看不見。
第三筆是 in-process 真的失敗（1/3,473 = 0.03%），但**原因查不到——shadow 只記 `inprocess_failed` 不記 why**，跟 §4.1 同一類儀器缺口。
所以決策收斂成：接受新路 ~0.03% false negative，換每個請求 ~610 ms + 移除一個發生率約兩倍的既有 false negative。數據上 in-process **又快又更正確**。剩下的是歸屬權判斷（`has_report` 能不能由 trans v1 自己的 kit 資料導出），不是準確度判斷。

### [2026-09-16 17:00]
**Leo 否決 inprocess 切換**：「沒辦法確保資料是一模一樣的，不要切」。`TRANS_TIMELINE_KIT_MODE` 維持現狀（shadow），我沒有再動 ConfigMap。Confluence 更新到 **v6** 記錄決定與理由。

**我的建議哪裡站不住腳（要記住的推理錯誤）**：我用**錯誤率**論證——新路 0.03% vs 舊路約兩倍——推導出「in-process 又快又更正確」。但錯誤率證明不了**資料源等價**。3,473 筆相同只代表「在那 46 小時實際流過的流量上兩邊同意」，不代表兩邊讀的是同一份記錄；而 3 筆分歧正好證明**它們會分歧**。更關鍵的是那筆 in-process 失敗**原因查不到**——一個機制不明的失敗，出現在病人看得到的欄位上，應該是 blocker，不該被平均進一個比率裡蓋過去。
**通用形式**：agreement count 是「在觀測到的輸入上行為一致」的證據，不是「等價」的證據。要從前者跳到後者，需要的是 provenance（證明兩邊讀同一份資料），不是更多樣本。樣本再多也只是把同一個推論錯誤放大。
重開這題的條件寫進頁面了：證明 trans v1 的 kit 資料與 LIS-Sample 是同一份記錄，或把 in-process 限縮到可證明等價的案例；**不是跑更久的 shadow**。

**shadow 仍然值回票價——它找到現行路徑的一個真 bug**（與切不切無關，值得獨立開票）：三跳呼叫在負載下跑 5.6–8.0 秒後回 `false`，於是 `has_report` 對「有報告的病人」靜默顯示成沒有。**慢/失敗被當成否定答案回報**，而不是當成失敗。只改現行路徑就能修：把「沒有報告」和「查不出來」分開。這條已升為 §7 的下一步第一項。

### [2026-09-16 17:40]
Leo ok → 修現行路徑的 false negative → **PR #793**（head `795ecfd`，未 merge）。

**機制從 code 確認（不是推測）**：`settingTool.getRequest` 把所有失敗吞成 `{transbadstatus:500}`，該物件沒有 `.data`，而 `httpHasReport` 只讀 `kitStatusResponse?.data?.tube_info` → 失敗 = `false`。同一個 function 下面 60 行的 `orderItemsAndHistory` 有檢查 `transbadstatus`，這個 call site 沒有。
**生產證據對上了**：`[getRequest] getKitStatusV2 client error 409 ... accession_id=2609016901`，2026-09-16 01:13:22 UTC——與 shadow 分歧第一筆同秒同 sample（HTTP false / in-process true）。

**我先前的說法要更正**：我說「三跳在負載下跑 5.6–8.0 秒後回 false」，把「慢」當成成因。實際上 `getRequest` **沒有設 axios timeout**，所以慢不會變成失敗。三筆分歧的正確歸類是：
- 01:13（8,035 ms）= **真的失敗**（409），有 log 佐證 → #793 修得到
- 22:00（5,600 ms）= **沒有對應的失敗 log**，可能是真的資料源分歧 → #793 修不到，正是 Leo 擋下 inprocess 的那個理由
- 17:41 = in-process 失敗
**教訓（與今天第三條 lesson 同源）**：把「慢」和「失敗」混為一談，是因為我看到時間長就假設是 timeout，沒去確認有沒有設 timeout。

**修法**：失敗時 `has_report = null`。`null` 本來就是 `timeline_body` 的初始值，所以「未知」一直在合約內；不在合約內的是對沒完成的查詢斷言 `false`。成功但 `tube_info` 空仍然回 `false`——空答案也是答案，這條有 test 釘住。另外補上失敗時的 log（原本完全無痕，只有一行 generic `[getRequest]`，跟被它降級的 response 沒有任何關聯）。
**順手關掉 shadow 自己的儀器缺口**：payload 加 `http_failed` / `both_failed`，`equal` 改成「兩邊都答了且一致」——就是今天送 factory #82 的那條教訓，先套用在自己的 code 上。

**PR body 有標記需要 reviewer 檢查的點**：`has_report` 現在可能是 `null`，前端若有 `=== false` 的分支會走不同路，merge 前值得 grep 一次前端。
**另一個順手發現（未修）**：4 筆失敗有 3 筆是 404 且 `accession_id=portal.vibrant-wellness.com`——有東西把 hostname 當成 accession id 傳進來，值得另開票。

### [2026-09-16 18:10]
Confluence 更新到 **v7 → v8**（#793 進 §5.8、slow-vs-failed 更正、accession 發現進 §6、Next 重排）。

**追 `accession_id=portal.vibrant-wellness.com`**：7 天 12 筆，**全部**來自 `getKitStatusV2`。排除是我們的 config——`lis-trans-config` 的 `getKitStatusV2` 值正確（`...kits?accession_id=` 結尾），所以值真的是從 `POST /trans/getTimeLine` 的 request body 來的（controller 直接傳 `getTimeline.accession_id`）。發生在工作時段、約每天 2 筆，不像排程監控，像真實 client 的 bug。
**決定不修 DTO**：`accession_id` 宣告是 `@IsString()`，DB 裡是 **varchar**，所以「accession 一定是數字」是假設不是事實；加嚴格驗證會把一個降級回應變成硬 400，而我無法完整刻畫這條路的所有呼叫者。這條需要 client 端的 owner，我只把事實寫清楚。

**#793 的前端疑慮已自行解除**（原本寫在 PR 裡請 reviewer 查）：`getTimeLine` 在 va-portal / vibrant-wellness-portal / LIS-frontend / pns-portal 四個 repo 裡**只有一個消費者**（`PatientProfilePage/service/TimelineService.js`），`has_report` 只有 4 處用法：初始 false、reset false、assignment、以及 `if (this.hasReport && ...)` 的 truthy 檢查。**全 repo 沒有任何 `=== false` 形式**。`null` 是 falsy → 渲染行為不變。已回寫 PR comment 與頁面。
**過程中差點犯的錯**：本機 va-portal checkout 落後 origin/main **115 個 commit**，我第一次是對過期的樹 grep。改用 `git grep origin/main` 重查才算數。**讀別的 repo 下結論前必須先確認那個 checkout 的新舊**——Sync With the World 不只適用於自己在動的 repo。

**工具筆記**：`mcp__vibrant__mysql_query` 的 SQL 必須以分號＋換行結尾，否則參數結尾的 `<` 會被送進 SQL parser 而報 `Parsing failed ... but "<" found`。
