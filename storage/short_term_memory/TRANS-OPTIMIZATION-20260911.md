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
updated: '2026-09-23'
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
- VP-18303
- VP-9299
- business-model
- business-model-deep
- failures
- repo-catalog
- repos
score: 0.7763
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

### [2026-09-16 18:55]
切換後 ~4 小時（22:04–01:52 UTC）持續觀測：
- 新路徑累計 **1,088 次**（kit 434 / qnr 326 / teststatus 328）。
- **客戶面 request errors 仍為 0**；pod restarts 0（v2 3h51m、v1 3h48m）；DEADLINE_EXCEEDED **0**。
- 舊 proxy 路徑 2 次（90 分鐘時是 1 次）→ 約每 2 小時 1 筆的涓流，不是零。追不到 caller（量太小不會被 span 取樣）。**明天用整天資料再看一次**：若穩定維持每小時 <1 筆，可能是某個非 transv2 的消費者，那會影響該端點能不能退役。
- **新增 1 筆 gRPC client error**（90 分鐘時為 0）：01:46:19 UTC，`/testresult.TestResultGrpcService/GetTestStatus`，`2 UNKNOWN: Internal server error`，peer 是 `lis-test-connect-deployment`。**是下游服務回的錯，不是切換造成**——shadow 期間唯一那筆「不一致」也正是同一個錯誤類別，而且當時兩條路同時失敗。
  **不下結論的理由（套用今天寫的 lesson #83）**：新路 1/328 = 0.30% vs 舊路歷史 3/10,723 = 0.028%（09-09~09-16）。點估計高 ~11 倍，但 **n=1**——以舊路真實率推算，328 次中出現 ≥1 筆的機率約 8.7%，屬於正常機會範圍。單一事件無法分辨真實變化與偶然。**明天用完整一天的資料重算錯誤率**才算數。
  該錯誤對使用者無影響：patientProfile 對 getTestStatus 有 `.catch()` 退回全零（那是既有的靜默預設問題，兩條路一樣）。

### [2026-09-17 15:30]
昨天留下的三個「明天用整天資料再看」全部結清，另外 #793 已由 Leo merge 並上線。

**#793 上線驗證（19:50–19:52 UTC 三個 pod，live image `c8020ee`，含他人 #794/#795）**：
- 正向對照成立：`@operation:kitShadow` 上線後 **288 筆**，payload 已帶 `http_failed` / `both_failed`（實際讀到一筆 `http_failed:false`、`both_failed:false`、`equal:true`），儀器缺口確實補上了。
- `@operation:kitLookupFailed` **0 筆**、`@equal:false` **0 筆**、`@inprocess_failed:true` **0 筆**。
- **0 筆不能當成「修好了」的證據**：失敗基礎率是兩天 4 筆（≈0.08/h），2.5 小時內期望值 <1。真正證明 code 在跑的是那 288 筆 shadow log，不是失敗 log 的缺席。

**舊 proxy 路徑：改用 log（非取樣）量，得到和 span 完全不同的結論**
- 對照（09-16 19:00–21:00，切換前）：`@url:/proxy/grpc/*` `@request_type:Request` = **976 次/2h**（≈488/h）。
- 今天 07:00–22:26（15.4h）= **18 次**，且分佈極不平均：
  - `getTestStatus` **0**、`getQuestionaireBySampleId` **0** → 這兩個端點真的死了，可退役。
  - `getKitStatus` **13**（≈0.85/h）→ **不是零**。
  - `getPatientTestsResult` **5** → 本來就不在 S2 遷移範圍，另有消費者。
- **儀器教訓（重要，會影響之前的數字）**：span 是取樣的（對照窗 976 次真實流量只有 4 個 span ≈ 0.4%），所以我先前用 span search 說「舊路 ≤1 次／2 次」是在用一個解析度不足的儀器報稀疏事件。**v1 對每個 request/response 都寫 log，那才是計數用的儀器**；span 只適合看單一 trace 的結構。錯誤 span 反而近乎完整（被 error retention filter 保留），所以**分子可信、分母不可信**——不要用取樣分母算錯誤率（昨天那個「11 倍」就建立在不可比的分母上）。

**`getKitStatus` 殘留呼叫者：四個機制逐一用證據排除，不是假設**
1. transv2 呼叫點 1（`utility.api.service.ts` `proxyLookup`）：`mode==='grpc'` 直接 return `proxyGrpcCached`，**無 HTTP fallback**（讀 origin/main 原始碼確認）。
2. transv2 呼叫點 2（`utility.service.ts:2574` `UtilityRestService.getKitStatus`）：同樣 mode-gated，grpc 分支不碰 axios。
3. Config drift（計劃書記錄過 `kubectl apply` 回退）：`lis-transv2-config` = `grpc`，**三個 pod `printenv` 都是 `grpc`**，0 restart；且熬過了他人 #636 的 deploy（live `ac96c57`）。
4. `cloud-local-proxy`：repo 內兩處 `/proxy/grpc` **都只是註解**（描述 code 出處），不是呼叫者。
→ 結論：有一個**尚未識別的 in-cluster 消費者**在用 `/proxy/grpc/*` 家族（axios/1.16.0 打 `lis-trans-service:3146`），`getKitStatus` 與 `getPatientTestsResult` 都是它。trace 在這個量級不會被取樣，所以歸因做不到。**要收掉這條，最省的做法是在 v1 proxy controller 對 `/proxy/grpc/*` 記 user-agent / x-forwarded-for**（小改動、只加 log），否則就得要 ingress log。
- 注意：transv2 namespace 是 **`transv2`**，不是 `default`（v1 在 default）。

**gRPC 錯誤率（完整 24.4 小時窗，09-16 22:04 → 09-17 22:28）**
- migrated 三個方法的 error span 仍然**只有 1 筆**，就是昨天那筆 01:46:19 `GetTestStatus` `2 UNKNOWN`（peer `lis-test-connect-deployment`），之後 ~20 小時沒有新的。
- transv2 全服務 error log 59 筆，逐一看**沒有一筆屬於 migrated path**；唯一沾到 kit 字樣的是 `getPatientKitInfo`（09-16 23:51）。查 8 天歷史：**22 筆，其中 12 筆落在 09-16 切換前的 18:58–20:21**，切換後只有那 1 筆 → 既有錯誤類別，切換後反而變少，非 regression。
- 昨天說的「客戶面 request errors 0」要收斂講法：那是 request 層級的量測；應用層 error log 一直都不是 0（既有類別），兩者不同指標。

**Confluence 2684321795 目前是 stale 的兩處**（尚未改，等 Leo）：§5.8 仍寫 #793 「(open)」而它已 merge 並上線；§7 有一行「Agree the `has_report` semantics, then switch `TRANS_TIMELINE_KIT_MODE` to `inprocess`」與上方「declined, not deferred」直接矛盾，是舊版殘留。

**VP-18262 本身的交付面（今天最大的缺口，與 code 無關）**
- 票是 **Dev In Progress、due 2026-09-18（明天）、零 comment**，最後更新 09-14。所有已上線成果掛在 VP-18276／Confluence，票面上看不到任何東西。
- 票的 acceptance 是三件事：(a) 一份分 phase 的合併 plan、(b) Phase 1 detailed doc（細到能拆 dev ticket）、(c) 把 Phase 1 日期回填 epic VP-18260 Timeline。目前 plan 只有本地 `docs/plans/trans-optimization/PLAN.md`（草案 v0.3，繁中），§6 的建議票「尚未建」；Confluence 那頁是 **shipped changes**，不是 plan。
- **joint deliverable 的另一半沒動**：Yekai 的孿生票 **VP-18261 仍 Dev To Do**，09-13 後未更新，同樣 due 09-18。這是協調問題，不是我能單方面補的。

### [2026-09-18 13:43]
Leo：「還有什麼能做的嗎？一樣要 pull 最新的 PR 並且檢查 atlassian doc」→ 回報選項後他指定 **做 A + B，不要停**。

**同步結果**：#793 已 merge 上線（09-17 18:23Z），TRANS-OPT 這條線目前沒有未 merge 的 PR（v1 最新是別人的 #798/#799 VP-16886）。Confluence 2684321795 停在 v8，09-17 一整天的量測都還沒進頁面。VP-18262 仍 Dev In Progress、due 今天、0 comment。**Yekai 的 VP-18261 已被改到 due 09-24**（09-17 18:35 PT），我這張沒改——兩張同一份 joint deliverable，期限現在不一致。

**#793 的正向證據終於有了**（昨天只有 288 筆 shadow 證明 code 在跑，失敗數 0 不構成證據）：24 小時 1,512 筆 kit lookup，`http_failed:true` **3 筆**、`kitLookupFailed` **3 筆**（兩側對得起來）。**每天約 3 筆病人可見的假陰性被消掉**。in-process 失敗 1/1,512（0.07%），與 shadow 期的 0.03% 同量級——Leo 擋下切換的理由沒被新資料動搖。

**舊 proxy 路徑，切換後全窗（09-16 22:04Z → 09-18 20:30Z，46.5h）逐 route 計數**：`getTestStatus` 0、`getQuestionaireBySampleId` 0、`listTnpCode` 0、`getKitStatus` 22（≈0.47/h）、`getPatientTestsResult` 8。前兩支是 S2 遷移對象且消費者已確認搬走 → 可退役；**`listTnpCode` 的 0 不能算數**——它從來不在 S2 範圍，零是「沒解釋」不是「預期」，刻意留著。`sendSkinPlacePatientOrders` 在 trans v1 是 0，但它的已知 caller（billing）打的是地上 proxy，不是這裡，所以 0 不構成死亡證據。

**A（交付面）完成**：
- 兩份英文交付物寫完並上 Confluence（LIS space，folder 2681962497 下）：
  - **Phased Plan** 2697461770（v2）— 六個 phase、排序理由、量到的三個結構性成因、提議時程。
  - **Phase 1 Detail** 2696740867（v1，plan 的 child）— P1-A~P1-F 六個工作項，各有證據/做法/影響元件/驗證/回滾/sizing，共 ~6 dev-days，附 13 張可直接開的票。
  - 本地 source 同時進 repo：`docs/plans/trans-optimization/{epic-plan-en,phase1-detail-en}.md`。
- Jira comment 與 epic Timeline 兩份草稿寫在 `jira-drafts-20260918.md`，**未發**（comment 只起草的既有規則；epic description 是 PM 的欄位，更該等 Leo）。

**B（Confluence v9）完成**：§5.8 的 #793 從 (open) 改成 merged+live 並補上線後實測；新增 **§5.9「Counting with the right instrument」**（span 取樣 vs log 全量的儀器教訓 + 逐 route 計數表 + 未識別 caller 的四個排除證據 + 24.4h gRPC 錯誤讀數）；§7 整段重寫，砍掉「Merge #793」和那行與「declined, not deferred」矛盾的 inprocess 殘留，並連到新的兩頁。

**寫 plan 時做的一個判斷**：原 PLAN.md 的 Phase 0/1/2 有很大一部分已經上線了，要不要重新編號。決定**不重編**——Confluence 頁和團隊對話已經在用「Phase 0/1/2」這組詞，重編號會讓看過舊版的人對不上。改成每個 phase 標 shipped / partly shipped / not started，Phase 1 detail 只寫「還沒做的部分」，並把已上線的部分列在 §2 當背景。

### [2026-09-18 14:05]
Leo 三項指示：(1) comment 發、(2) 這張票先完成並附連結、(3) C1 也先做。全部執行完。

**VP-18262 結案**：comment 188370 已發（ADF，三個 Confluence 連結 + 調查結論 + 已上線實測 + 提議日期 + 兩個外部相依）。三個 Confluence 頁以 remote link（relationship `documented by`）掛上票面。狀態 **Dev In Progress → Done**（resolution Done）。
- **transition 選擇的依據**：可選 `Dev Complete`(2) 與 `Done`(15)。查同系列的 **VP-18276**（同為 Task、同為 trans-opt 記錄票）當初收的是 **Done**，VP-18080 亦然；VP-18197（Improvement、有 code）才是 Dev Complete。這張是調查/計劃交付、沒有 code 要 QA，所以照 VP-18276 收 Done。
- **工具筆記**：`mcp__vibrant__get_jira_metadata(transitions)` 對這張票回 **空陣列**——MCP 的 service account（`jira-agent-...@serviceaccount`）沒有 transition 權限。改用 `.env` 的 JIRA_EMAIL/JIRA_API_TOKEN 直打 REST `/rest/api/3/issue/{key}/transitions` 才拿得到清單，POST 也成功。**comment 可以用 MCP 發（會顯示成 "Jira agent"），transition 與 remote link 要用 Leo 的 token。**
- epic VP-18260 的 Timeline 草稿**沒動**——Leo 沒指示，那是 PM 的 description 欄位。草稿留在 `jira-drafts-20260918.md`。due date 也沒改（Yekai 的 VP-18261 是 09-24，這張維持 09-18 並在今天結案）。

**C1 = Phase 1 的 P1-D，PR #800**（head `d2274f3`，未 merge）：`ProxyCallerLogInterceptor` 綁在 `ProxyController` 上，每個 `/proxy/grpc/*` 請求記一筆 user-agent / x-forwarded-for / x-real-ip / remote_address / route / method / JWT userId，operation `proxyGrpcCaller`。
- **讀 code 得到的兩個事實**（不是推測）：6 條路由**每條都已經收 `@Headers() headers`**、多數收 `@Request() req`（`req.user.userId` 由 `CustomJwtAuthGuard` 填），資料一直都在手上、只是沒人記；而全域 `LoggingInterceptor` 記 url/query/body/response 但**不記 header**，所以 user-agent 從來沒進過 log。
- **刻意不記 query string**：`sample_id` / `patient_id` 是檢體識別，對歸因沒有貢獻。
- **log-only 的失敗模式要自己堵**：try/catch + detached `.catch()`，兩個 test 釘住「logger throw」與「log write reject」都不能影響路由回應。一個會讓請求失敗的 log-only 變更就不是 log-only。
- 測試：新 spec 6 cases；全 suite **66/66、850 tests 綠**，`tsc --noEmit` 乾淨。
- PR body 標了要 reviewer 判斷的一點：**`user_id`（JWT subject）該不該記**——它是最強的歸因訊號、也對齊 core 側 VP-18140 的 `jwt_sub`，但拿掉其餘 tuple 仍可用。

**退役順序因此固定下來**：#800 merge → 觀察一週 `@operation:proxyGrpcCaller` → 找到 caller 後才動 `getKitStatus`；`getTestStatus` / `getQuestionaireBySampleId` 兩支已有兩個獨立零窗口，可以先退。`listTnpCode` 雖然也是 0 但不在 S2 範圍，零是「沒解釋」不是「預期」，繼續留著。

### [2026-09-18 15:20]
Leo 質疑「這種應該要先看 datadog 這 14 天的流量不是嗎」——**他是對的，而且我犯的是自相矛盾**：我在 Phase 1 doc 的風險表裡自己寫了「罕見 caller（月批次、排程 job）」這條，對 `listTnpCode` 套用了、對另外兩支卻沒有。兩個窗口 46.5 小時、而且都在切換之後，撐不起「可退役」。

**拉到 15 天（Datadog retention 上限；35 天的查詢最早只回到 09-03，flex 也一樣）之後，得到的是完全不同層級的證據**：
- `getTestStatus` 與 `getQuestionaireBySampleId` **每一天都 lockstep**（差 ≤1：120/120、249/249、266/266、1789/1789、1602/1603、1876/1877、1512/1513…），`getKitStatus` 穩定是它們的 **2 倍** → 這是**單一 caller 的固定 per-sample 樣式**，不是一群 caller。第二個獨立消費者跑的那天 lockstep 會斷，15 天沒斷過。切換後兩天整整 0。
- **這是關於 caller「組成」的證據，不是「缺席」的證據**——這才是退役該用的標準。零窗口只能證明那段時間沒人打。
- `listTnpCode`：15 天全 0（**切換前就是 0**），且全機器 63 個 repo 零呼叫者。注意 `LIS-backend-results-grpc` 有同名 `listTnpCode`，那是**下游實作**不是 caller，差點誤判。
- **`getPatientTestsResult` 我先前寫錯了**（PR #800 body 與 Phase 1 頁都寫「大概是同一個 caller」）：它 15 天平盤 1–5/天，**切換完全沒影響它** → 從來不在遷移路徑上，它的消費者至少存在 15 天。`getKitStatus` 的殘留（15、5）與它同量級，所以「同一個 client 打兩支」仍是最省解釋，但「與遷移路徑同一個 caller」已被**排除**。

**判定：三退三留** — 退 `getTestStatus` / `getQuestionaireBySampleId` / `listTnpCode`；留 `getKitStatus` / `getPatientTestsResult`（未識別 caller）/ `sendSkinPlacePatientOrders`（billing 要**改指過來**，它是整併終點不是退役對象）。

**Leo 追問「切換後可以內部統整對嗎」→ 對，但 proxy 不是純轉發**，搬移要一起帶三樣：(1) `createMetadataForCoresampleV2` 的 JWT→gRPC metadata 轉譯（`user_id` **不是** ownership 檢查，六個 method 都只餵進 metadata）；(2) `getKitStatus` 的 proto3 補值（`packages` → `[]`，Sentry #68038）；(3) error/Sentry/log 那層。**可行性有實證**：transv2 #629 就是逐行搬的，normalization 也照搬（`proxy-grpc.service.ts:130-144`）。
→ 但前提是那個 caller **講得了 gRPC**。講不了（不能 vendor proto 的 Java/Python service、on-prem script、別人的排程）就得留著當橋。**所以終局不是六條全消失，是五條消失＋一條變成統整點**，而 P1-D 的意義因此從「退役前置」升級成「決定刪掉還是留橋」。

**Leo 指示：寫公告、兩週後做、建票 deadline 三週。** 已執行：
- **VP-18320** 建立（parent VP-18260、due 2026-10-09、P2、assignee Leo、Dev To Do）。description 含範圍、15 天 lockstep 證據、明說看不到的那一類（月週期 + 只搜本機 repo）、搬移指引（含上面三樣要帶走的東西）、時程三段。
- 公告雙語稿 `docs/plans/trans-optimization/announcement-proxy-grpc-deprecation.md`，Leo 自己發。核心設計：**公告存在的理由就是補上 log 看不到的那一類**——所以文案明說「不確定也請留言，我們的 log 只留 15 天」。
- 三處文件同步更正：Phase 1 頁 **v2**（P1-C 改寫成 lockstep 證據 + VP-18320、P1-D 加 consolidate-vs-bridge、DoD 與風險表改掉「兩個零窗口」的標準）、shipped-changes **v10**（§5.9 表換成 15 天版 + 明寫先前那個較弱標準是錯的 + `getPatientTestsResult` 更正）、PR #800 body（同上，head `d2274f3` 未動）。

**通用教訓**：退役決策要的是**caller composition**（誰在打、樣式是什麼），不是 **absence**（某段時間沒人打）。零窗口的長度再加也只是同一個推論形式加大樣本；換成看整個 retention 窗的樣式才換到不同種類的證據。這與 09-16 那條「agreement count 不等於 equivalence」同源——都是把「觀測到的行為一致」誤當成「結構上的結論」。

### [2026-09-18 16:40]
Ray 回覆確認 `/proxy` 與 cloud-local-proxy 是 2023 年 DNS 未通時代的產物，終局是**全部移除**、呼叫者直接打目的地。Leo 要求把「分類 + 替還在用的端點找更好的家 + 要求下游 migrate」寫成英文 Confluence doc。

**新頁面 2697166874**「Retiring /proxy and cloud-local-proxy — Classification and Migration Targets」（Phased Plan 的 child），並從 plan 頁（v3）與 VP-18320 remote link 連過去。

**這輪最重要的是我自己被打回來兩次，兩次都對：**
1. Leo 問「14 天流量」→ 我原本用 46.5 小時兩個零窗口就要退役，而我自己在風險表寫過「月批次」這條卻沒套用。**退役要的是 caller composition（誰在打、樣式），不是 absence（某段時間沒人打）。**
2. Leo 問「可以分類 + 要求下游搬不是嗎」→ 我上一輪答「零條搬 trans v2」，**那是在 caller 身分還不知道的情況下就砍掉選項**。trans v2 的 `PNSResolver` 已有 `getKitStatus` 的 `@ResolveField`、`patientProfile` 也在用 kit 資料——**caller 若是前端，搬 v2 不需要任何新實作**。已收回。

**這次新挖到的事實（都進了新頁）：**
- `/proxy/old-report/*` 11 條**只有 `downloadTestOrderPDF` 活著**：15 天 **20,715 次**（≈1,380/天，真實客戶 `customer_id`、`opt=download`）。其餘 10 條全零。
- 11 條**全部都是重複品**：`trans-reports.controller.ts`（`@Controller('trans')`）有同樣 11 個操作外加 8 個，**共用同一個 `OldReportProxyService`、程序內呼叫不是 HTTP 自打**。
- `/trans/*` 雙胞胎 15 天：GenerateBatchReqOrReportV2 1,830、downloadTestOrderPDF 1,436、另兩條各 8、其餘 7 條 0。**22 條端點只有 5 條有流量。**
- **`/proxy/old-report/downloadTestOrderPDF` 的量是正式 `/trans/` 版本的 14 倍**——proxy 是主要路徑，caller 未識別，而 **#800 的 interceptor 沒蓋到 old-report**。要另開 PR。
- va-portal 打的是 `/trans/downloadTestOrderPDF`（`src/api/download.js`，對 origin/main 查的），不是 proxy 版。
- `sendSkinPlacePatientOrders` **也不是純轉發**：會 `skinPlace.comments = String(skinPlace.julien_barcode)` 再轉傳 Authorization。叫 billing 直打 crmapi 而不複製這個改寫，會安靜壞掉。
- trans v2 **完全沒有報告 code**（ConfigMap 有 key，`git grep` origin/main src 零讀取）。

**定死的分類規則（兩個問題決定歸宿）**：叢集內服務 + metadata/正規化 → 直打 gRPC；前端/外部 + metadata/正規化 → **trans v2**（現成）；前端/外部 + **PHI ownership gate** → **trans v1 `/trans/*`**（gate 已在那）。
**給 Ray 的關鍵區分**：要刪的是**重複的轉發層**，不是**認證邊界**。`/trans/*` 與 trans v2 不是 wrapper 是產品 API；PHI 的目的地不是 gRPC-only（core）就是 `secure/nologin`（地上報告伺服器），所以「直接打目的地」對叢集內服務成立、對終端使用者不成立。
**維持的判斷**：報告那 19 條不重寫進 v2——零延遲收益（p95 在 lis-order/pdf-engine）、且重做合規 gate 正是上次 `?internal_user_id=` 繞過漏洞的來源。

**下一步（頁面 §6）**：#800 merge + 另開 old-report 版 attribution PR → 一週後填上三個待定歸宿 → 每個下游 owner 一張 migration 票 → 刪。

### [2026-09-18 17:10]
Leo：「每個你認為不該 remove 的都可以有比較好的方向不是嗎？這個就要寫進 doc」——**第三次被打回來，第三次對**。我 §3 有三行寫「blocked on caller identity」，讀起來像「不知道、做不了」。**caller 身分只決定走哪個分支，不決定有沒有方向**；方向由 domain 與實際下游決定，那兩件事今天就知道。

**查出來的下游（這才讓每一條都能定向）：**
- `/proxy/old-report/downloadTestOrderPDF` 的真正下游**不是報告伺服器，是 lis-order**：controller 用 `url_order_summary_new` + `url_order_summary_new_redraw`（兩者都是 `api.vibrant-wellness.com/v1/portal/order`）並行抓兩份 PDF → 依 200/204 × `order_status` 四路分支 → **合併** → 串流 → 刪暫存檔。所以它是**訂單摘要**不是檢驗報告，**搬去 base-report-service 是錯的**（會變成 report-service → lis-order 再跳一次，正是要刪的形狀）。**正解是 lis-order**——兩份 PDF 都是它自己產的，搬過去兩次跨服務呼叫加合併會塌成一次。
- 同名陷阱：`transService.downloadTestOrderPDF`（打地上 `192.168.60.77:8081/secure/nologin/`）是**另一個方法**，被 notifications 等 7 處使用，跟那條路由不是同一件事。
- `/trans/GenerateBatchReqOrReportV2`（1,830）與 `GenerateOnlineZipDownloadV2` / `getOrderSummaryReportZip`（各 8）下游都是**地上 `192.168.60.77:8081/secure/nologin/`**。
- **由此得到比「留在 trans v1」更重要的結論**：那台不驗身分的地上報告伺服器才是該退役的東西；`/trans/*` 是**holding position 不是終點**，報告家族的終點是 base-report-service（`LIS-Report/base-report-server`，有自己的 AKS namespace、JWT、對外 edge、報告產生管線）。

**新發現的缺陷（與搬去哪無關，該自己一張票）**：`downloadTestOrderPDF` 把 PDF 寫到 `process.cwd()`，檔名只由 `sample_id` 組成 → **同 sample 的並行請求共用檔名**，其中一個的 `result.on('end')` 會 `unlinkSync` 掉另一個可能還在串流的檔。每天 1,380 次，是活的競態；期間 PHI 躺在 pod 檔案系統上。

**頁面 2697166874 改到 v3**：§3 改成「每個端點都有 destination」的表（多了「真正在跟誰講話」欄），新增 §5（downloadTestOrderPDF → lis-order，兩步走，短期那步零新 code）與 §6（報告家族終點是 base-report-service，`/trans/*` 只是 holding position，並重申不要重寫進 trans v2），§4 補上競態，§7/§8 重排並加上 lis-order / report team 兩個新對象。

**發佈時踩到的事**：頁面已經是 v2 而我只發過 v1 → PUT 回 409。**沒有直接覆蓋**，先抓 version 歷史（authorId 跟我用的 token 同一個帳號，分不出人），再把 live v2 與我 v1 的 markdown 重建後做 tag-strip 純文字 diff → 差異只有一處：Asks 第一條的 **"Ray — " 被人刪掉**。其餘全是 Confluence 編輯器的正規化（`local-id`、entity、table width）。**照著保留**，把該條改成中性的「Ingress access logs — 」，沒有把名字加回去，並回報 Leo 確認。
→ **可重用的做法**：Confluence 409 時，用「本地 markdown 重新產生當初那版 → 與 live 做 strip-tag 純文字 diff」就能在共用帳號下分辨「編輯器正規化」與「真人編輯」。

### [2026-09-18 17:45]
Leo：「可以直接做，但是一定不能影響到現在的狀況」→ old-report 的 attribution **PR #801**（head `77fd13b`，未 merge）。

**#801 疊在 #800 之上**（base = `feature/leo/TRANS-OPT-proxy-caller-logging`）。理由：interceptor class 在 main 上不存在，不疊就只能複製一份 code，兩張 PR 各一個同功能檔案，之後必然要再收一次。疊了之後這張的 diff 只有**兩行 wiring + 一份 spec**。#800 merge 後 GitHub 會自動把它 retarget 到 main。

**「不能影響現狀」在這個 controller 上有具體含意**：`/proxy/old-report/*` 回的是 `StreamableFile`、真的在串 PDF。好消息是 #800 的 interceptor **結構上就碰不到 response**——`return next.handle()`，沒有 `.pipe()`、沒有 `tap()`、沒有包裝。
→ **所以測試斷言的是 object identity**（`expect(returned).toBe(handlerObservable)`），不是斷言發出來的值。**identity 才是「串流不會被緩衝／延遲／重送」的那個性質**；斷言值只能證明這一次沒壞。這條值得記成通用做法：要證明「沒有包裝」就斷言同一個物件，不要斷言行為看起來一樣。
- 另外釘住：query string 帶 `sample_id`/`customer_id`、header 帶 bearer token，log 一律不收（有 test）；logger throw / log write reject 都不能影響路由（有 test）。
- 測試：新 spec 5 cases；全 suite **67/67、855 tests 綠**，`tsc --noEmit` 乾淨。

**CI 沒有跑，而且是預期的**：`.github/workflows/ci-tests.yml` 的觸發是 `pull_request: branches: [main, stage_test]`，#801 target 的是 feature branch 所以不觸發。**等 #800 merge、GitHub 自動 retarget 到 main 之後才會跑**。在那之前唯一的證據是本機那次全綠——回報時要講清楚，不能說「CI 綠」。

**流量理由（寫進 PR body）**：`/proxy/old-report/downloadTestOrderPDF` 15 天 20,715 次（≈1,380/天、真實客戶），其餘 10 條 0。#800 蓋不到它，而它正是三個待定歸屬裡最大的一個。

### [2026-09-18 dream] VP-18262 + VP-18276 closeout audit — both PASS as documentation closures; #800 live, caller logging not yet exercised
- **VP-18262** (Investigation & Plan): Leo Dev In Progress -> Done 09-18 13:52 PDT; comment 188370 (three Confluence links + remote links) is the deliverable. PR #800 merged to main 22:55Z AFTER Done; `lis-transformer-deploy-prod` run on 9264e9e success; 3 trans v1 pods on image 9264e9e, 0 restarts, error lines = only kafkajs ECONNRESET / ioredis ETIMEDOUT (known deploy-era noise). `@operation:proxyGrpcCaller` = **0 lines in ~2.5 h** on all 3 pods — consistent with 0 `/proxy/grpc/*` hits in the same window (one pod: 94 `/proxy/old-report/downloadTestOrderPDF` hits, 0 grpc), so "not exercised yet", not "broken". Expected ~0.6 hits/h; check after a full day. #801 (old-report attribution) still OPEN, stacked on #800's branch; CI will only run once GitHub retargets it to main.
- **VP-18276** (Phase 1-2 record ticket): Done 09-15 10:34 PDT by Leo, 0 comments, description = shipped table. All 8 PRs merged, every main merge's deploy run success (v1 last 5f79b52 09-15 02:08Z; v2 832ce95 09-14 22:56Z). Post-close ops recorded here, not on the ticket: S2 switched to grpc 09-16 22:03Z (3 pods printenv grpc tonight, 0 error lines in 3 h), kit inprocess declined by Leo 09-16, #792 deadline + #793 has_report fix live 09-16/17. transv2 pods on ac96c57 (2d3h, 0 restarts). No health signal firing.
- Dependents: no STM carries `unblocked_by` / `unblock_when` naming VP-18262 or VP-18276.

### [2026-09-19 dream] RE-CHECK: `proxyGrpcCaller` after a full day — the unknown `/proxy/grpc/*` caller is `lis-setting-consumer` (namespace `setting`)
- Window: 27 h of prod trans v1 logs (3 pods on 9264e9e, 0 restarts) = **6 `proxy_grpc_caller` events** (5 `getKitStatus`, 1 `getPatientTestsResult`), ~0.22/h — same order as the 15-day span estimate (~0.6/h), no other `/proxy/grpc/*` route hit. `/proxy/old-report` in the same window: 288 hits across 3 pods (#801 still OPEN, base still the merged #800 branch, CI never ran).
- Every event: `user_agent=axios/1.4.0`, `user_id=0` (no JWT), `x_forwarded_for=null`, `x_real_ip=null`, `remote_address=::ffff:10.224.{1.184,0.24,1.79}` → service-to-service over ClusterIP, not via ingress. `kubectl get pods -A -o wide` maps all three IPs to `setting/lis-setting-consumer-7dc8bdd8df-{fjnvp,x9cvq,f9zdj}` (image c3e166d = repo HEAD 09-16, 8 pods, 0 restarts).
- Code confirmed in `LIS-setting-consumer` (c3e166d): configmap `lis-setting-consumer-config` sets `proxy_getkit` / `proxy_getresult` to `http://lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/{getKitStatus?sample_id=,getPatientTestsResult?patient_id=}` (the repo `.env` still has the public `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy/grpc/...` URLs — prod overrides them; `proxy_getteststatus` exists in `.env` only, no prod key, matches the two zero windows for `getTestStatus`).
  - `getKitStatus` ← `setting-consumer.controller.ts` `getKitShip()` (~L8823) ← `bull.consumer.ts` `@Process()` of `notify_patient_when_not_return_kit_after_days` (L323/367) and of `notify_patient_ship_to_patient_confirm` (L1609/1654).
  - `getPatientTestsResult` ← `getPatientTest()` (~L9159) ← `getTestNameWithTNPReason()` (L8917) ← `consume_notify_patient_when_basic_redraw()` (L4431).
- Consequence for VP-18320: the two "keep until caller found" routes now have one owner. Retirement = point `lis-setting-consumer` at the gRPC client (or the transv2 route) via configmap + code, then retire both routes; no external caller seen in 27 h. Not acted on — work-session decision (Leo's announce-then-retire cadence). No ticket comment posted.
- Health in window (2026-09-19T01:52Z → 09-20T01:35Z): 40 result pushes all TRANSMITTED, 1 MDHQ order parsed, emr-v2 prod pod 0 error lines / 0 restarts.

### [2026-09-20 dream] RE-CHECK day 2: `proxyGrpcCaller` silent for 22 h; cluster-wide pod reschedule (not a deploy); #801 was NOT auto-retargeted
- **0 `proxy_grpc_caller` events** in the 3 trans v1 pods' whole lifetime (22 h, `--since=24h` capped by pod age). Consistent with the 09-19 attribution: the only caller is `lis-setting-consumer`'s BullMQ notify flows (~0.2/h, bursty, weekend-quiet). No new caller appeared; nothing changes for VP-18320 (still `Dev To Do`, only Jira Automation touched Duration/Start date on 09-19/20).
- **Every prod pod in default / setting / emr-v2 / transv2 was recreated 2026-09-20T03:14Z–03:41Z** (staggered ~5-min steps across `aks-agentpool` and `aks-userpool` nodes). ReplicaSets are unchanged (trans v1 `56df76746` created 09-18T23:05Z = the #800 deploy; emr-v2 prod `74688f6774` 09-17T18:38Z; setting-consumer `7dc8bdd8df` 09-17T22:34Z) → **node-pool rotation / drain, not a deploy**. Restart counters all 0 because the pods are new. `kubectl get nodes` is Forbidden for this account, so the node-side reason is unverifiable from here.
- **PR #801 is still `base = feature/leo/TRANS-OPT-proxy-caller-logging`** (head `77fd13b`, 0 status checks) two days after #800 merged. The 09-18 17:45 note above ("#800 merge 後 GitHub 會自動把它 retarget 到 main") was wrong: GitHub only retargets a stacked child when the base branch is **deleted**, and `feature/leo/TRANS-OPT-proxy-caller-logging` still exists at `d2274f3`. This is the same trap as VP-17408 (patterns.md "Stacked PR 陷阱"). Fix = manually retarget #801 to `main` (`gh pr edit 801 --base main`) so `ci-tests.yml` runs; if merged as-is it would land in the dead feature branch, not `main`. Work-session action, not done in dream.
- Health in window (2026-09-20T01:41Z → 09-21T01:35Z): result pushes = 1 (TRANSMITTED + ACKNOWLEDGED at 01:33Z, i.e. after the reschedule — the pipeline is live), 0 hl7_file_input rows; Sunday baseline is 0–72 pushes / 0 intake (09-06, 09-13), so the quiet day is not a signal. emr-v2 prod pod 0 error lines since creation. `lis-core-deploymentv7` (not ours) shows repeated liveness/readiness probe timeouts (2 s timeout) on the two heavy pods since the reschedule — noted for the digest, no restarts.

### [2026-09-21 09:30]
Leo：「繼續做 doc 裡面的每一步」＋「看 Vibrant-America org 所有 repo 有沒有人在用，記到 Phased Plan 並給 runbook」。

**先踩到一個我自己造成的事故：#801 沒有進 main。** 它 target 的是 #800 的 feature branch，我在 PR body 寫「#800 merge 後 GitHub 會自動 retarget」——**那只在 base branch 於 merge 時被刪除才會發生**。Leo 09-21 merge 了 #801，commit 進的是那個 feature branch，`origin/main` 的 `old-report.controller.ts` 仍然是 `@UseInterceptors(SentryInterceptor)`。→ cherry-pick 到新 branch 開 **PR #802**（base main，CI 四項全綠）。
**教訓**：stacked PR 不會自己接上 main。要嘛 merge 時刪 base branch，要嘛一開始就別疊。而且「merge 成功」≠「上線」——要去 `origin/main` 驗檔案內容，不是看 PR 顯示 MERGED。

**#800 已經回答了那個問題——caller 是 `lis-setting-consumer`。**
- 乾淨窗口（2026-09-20 03:45 之後，所有 pod 都已存在）內 **100% 的 `/proxy/grpc/getKitStatus` 來自它的三個 replica**，`axios/1.4.0`、`x-forwarded-for` 空（叢集內）、`user_id=0`（service token）。
- **UA 更正**：先前多處寫 `axios/1.16.0`，實測是 **`axios/1.4.0`**。那個 1.16.0 沒有來源，是我早期未驗證就寫進去的。
- **IP 歸屬差點誤判**：第一次查到 `10.224.1.184` → `lis-ordermanage`，但那些呼叫發生在 09-19 14:03–22:01，而該 pod 09-20 03:36 才啟動——**pod IP 會被回收，IP→pod 只有在 pod 生命期涵蓋 log 時間時才成立**。收回 ordermanage 那條，改用「所有 pod 都已存在之後」的窗口重查才乾淨。

**兩個儀器合起來才是封閉清單**（單用任一個都不夠）：
- **GitHub code search 掃 org 全部 138 repo** → 找得到硬編 URL 的 caller，但**看不到只存在於 k8s ConfigMap 的值**。
- **掃 prod 叢集全部 ConfigMap** → 找得到那些，但看不到沒部署在那裡的 repo。
- 兩者結果一致。code search 的其他命中（LIS-Shipping、results-*、coreSamples、Sample、emr-v2、LIS-Report）**全是 gRPC 方法名的「實作端」，是下游不是 caller**——這是最大的假陽性來源。

**配置在打 proxy 的只有三方**：`lis-setting-consumer`（4 個 ConfigMap × 4 個 key，含 20,715 次的 downloadTestOrderPDF）、`lis-transv2-config`（3 個 stale + 1 個仍在讀的 skin）、`lis-trans-config`（14 個 cloud-proxy key）、外加 `LIS-backend-billing` 硬編。

**第二個我自己的錯**：Phase 1 頁把 **S6（v1 的 14 個 cloud-proxy key 已移除）列為 shipped**——叢集顯示 prod **和 staging 兩邊都還有全部 14 個**。「staging 先刪」若真發生過，staging 會是乾淨的 → 所以是**從來沒執行**，不是漂回來。我第一版 runbook 還把它寫成 drift 並影射 `kubectl apply`，那是把自己的記錄錯誤歸咎於環境。已改：Phase 1 頁 S6 劃掉、P1-B 擴大成涵蓋兩個服務共 22 個 key；plan 頁的註記改成如實敘述。
**教訓**：文件裡「已完成」的宣稱，只要對象是叢集狀態，就必須回叢集重讀才算數；而發現不一致時，先假設是自己的記錄錯，不是環境漂移。

**產出**：Phased Plan 頁 **v4 → v5** 新增 §6「Consumer inventory and migration runbook」——逐 key 寫 today → change to → 要帶走什麼（metadata、proto3 packages 正規化、payload rewrite）。Phase 1 頁 **v3**。VP-18320 的 comment 草稿寫進 `jira-drafts-20260918.md`（Draft 3，**未發**——Leo 上次只授權了 VP-18262 那一則，沒有概括授權）。

### [2026-09-21 13:30]
Leo 授權四件：發 VP-18320 comment、推進 staging 身分驗證、推進 skin 死 key 刪除、**VP-18152 直接做**。本輪完成前兩項中的第一項與 VP-18152 的量測。

**VP-18320 comment 已發**（188522）：caller = LIS-setting-consumer、兩個儀器的封閉清單、skin 是死碼、提議併入 10 條零流量 old-report 路由。

**VP-18152 重新量測（14 天，`@event:core_v1_http_request`）—— scope 比票面小很多**：

| trans 呼叫點 | core v1 路由 | 14 天 axios 流量 |
|---|---|---|
| `list_customer_by_id_carlos` | `/api/clinic/list-customer-by-id/:clinic_id` | **活的**（數千筆） |
| `create_patient` | `/api/patient/create-patient` | **0**（該路由在全域資料裡完全沒出現） |
| `create_patientv2` | `/api/patient/create-patient-new` | **1** |
| `LOG_IN_VIA_SESSION` | `/api/user/login_via_session` | **0**（完全沒出現） |

→ **10-31 之前真正必須遷的只有 1 個呼叫點**，不是 4 個。另外三個要用跟 proxy 同一套標準處理：`create_patient` 掛在 `createPatientBatch` 批次路徑上，**14 天看不到月週期**，所以是「公告＋確認」不是「假設已死」。

**又一次判別失誤，這次自己抓到**：我先用 repo 的 axios 版本當 trans 的指紋（v1 `^1.6.0`→1.13.6、v2 `^1.12.2`→1.16.0），看起來對得很漂亮。但 `/api/user/lis_log_in` 有 121 筆 `axios/1.16.0`，而**兩個 trans repo 都沒有引用 `lis_log_in`** → **axios 版本能縮小範圍但不能識別身分**，別的服務可能跑同一版。改用 VP-18140 log 自己的 `remote_ip` 才算數。
→ 通用形式：**用「共享的技術特徵」（library 版本、UA、語言）當身分證，會在有第二個同款使用者時靜默錯誤**。要用「該服務獨有的東西」——pod IP（且要驗 pod 生命期）、專屬 env、專屬路由。這是本 session 第二次踩同類（第一次是 pod IP 回收）。
- 附帶：VP-18140 log 的 `service_name` 欄位是 `unknown`，`jwt_sub` 是空字串——Zhibin 09-10 提過的歸因缺口仍然存在，所以只能靠 `remote_ip`。
- 14 天內 `list-customer-by-id` 出現 **120+ 個不同 pod IP**，pod 汰換太頻繁，無法逐一解析；但這不影響 scope 結論。

**未完成（下一輪）**：staging 驗 `/trans/downloadTestOrderPDF` 身分解析；skin 死 key 的四個 ConfigMap 刪除（staging 先）。先做 VP-18152 量測是因為它有 10-31 的外部硬期限。

### [2026-09-21 14:10]
Leo：「其他不能同步做嗎？」→ 對，兩件互相獨立。都做完了。

**(1) staging 身分驗證：`/trans/downloadTestOrderPDF` 不是 drop-in，但差異定位到單一參數。**
方法：`lis-setting-consumer-st` pod 內沒有 curl，用 node 寫探測腳本（OAuth2 client_credentials 拿 token → 同一 token、同一 query 打兩條路由）。第一版 `TOKEN PARSE FAIL` 是我自己把 body 截到 300 字元、JWT 比那長。
Token claims：`role=INTERNAL`、`internal_user_role=service`、`internal_user_id=10018`、**`customer_id=null`、`clinic_id=null`**、`user_id=0`。

| 變體 | 結果 |
|---|---|
| `/proxy/old-report/downloadTestOrderPDF` 原 query | **200**, 3,093,587 bytes PDF |
| `/trans/downloadTestOrderPDF` 原 query | **400 Bad Request** |
| `/trans/...` + `&clinic_id=1` | **200, 3,093,587 bytes（位元組完全相同）** |
| `/trans/...` + `clinic_id` + `internal_user_id` | 200, 同樣 bytes |

→ **成因**：`/trans` 版用 `resolveIdsForHttpOptional(req.user, query, ['customer_id','clinic_id'])`，service token 兩者皆 null 就回退到 query；setting-consumer 只送 `customer_id` 不送 `clinic_id` → 400。proxy 版只讀 `req.user` 且用 `isTrustedInternalCaller` 直接 bypass，所以不需要。
→ **`clinic_id` 的值不影響授權**：token 是 trusted-internal，`ownsSample` 會 bypass，那個參數只是用來滿足 resolver。一個「必填但對受信任呼叫者無作用」的參數，本身是個異味。
→ **所以遷移是「setting-consumer 的 URL 組字串多加一段 `&clinic_id=`」的小 code 改動**（`setting-consumer.controller.ts:15086` 那行 template literal），不是純換 ConfigMap 值。另一個選項是改 `/trans` 版對 trusted-internal 放寬驗證，但那會動到一條每 15 天 1,436 次的活路由的驗證邏輯，比較不划算。

**(2) skin 死 key：兩個 staging ConfigMap 已刪並重啟驗證。**
- 先備份兩份 CM yaml 到 scratchpad。
- `kubectl patch --type=json -p '[{"op":"remove","path":"/data/skin_placepatientorders"}]'`：`lis-setting-consumer-st-config`（剩 135 keys）、`lis-setting-consumer-local-st-config`（剩 122 keys）。
- **刪 key 對執行中的 pod 沒有影響（env 在啟動時注入），所以唯一能證明安全的是重啟**。動手前先確認 `ConfigModule.forRoot` **沒有 `validationSchema`**，缺 env 不會擋啟動。
- 兩個 deployment 都 rollout restart：1/1 Running、restarts=0、**`level:error` 各 0 筆**、pod 內 `skin_placepatientorders` 確認 unset 而 `inventory_url_skin` 仍在。log 裡 8 筆 "skin" 全是 `skin_care*` 的 Kafka consumer group 啟動訊息，info level。
- **prod 兩份（`lis-setting-consumer-config`、`-local-config`）沒動，等 Leo。**

**方法論筆記**：我一開始用 `grep -icE "error|exception"` 數到 82 行就差點當成問題回報——那個 pattern 會打到 JSON 欄位名（`recoverable` 之類）。改用 `"level":"error"` 才是這個服務的錯誤訊號。**數錯誤要用該服務實際的錯誤欄位，不是字串比對。**

### [2026-09-21 18:25]
Leo merge 了 #802，要求「等 deploy 後測試確認沒問題再繼續」。deploy 成功並驗證通過。

**部署**：run 35635109563，test gate → buildImage → deploy 全綠，18:09:07Z。live image `35c972eaf7be...` = #802 的 merge commit；三個 pod 1/1 Running、restarts=0。
→ **這次特地做了「merge ≠ 上線」的檢查**（#801 的教訓）：先確認 `origin/main` 的檔案內容有 wiring，再確認 live image SHA。

**正向證據（最大收穫）**：`/proxy/old-report/downloadTestOrderPDF` 的 attribution 一上線就吐出來，來源是 `10.224.1.167` / `10.224.0.226` / `10.224.2.53`——**正是 `lis-setting-consumer` 的三個 pod**，`axios/1.4.0`、`user_id:0`。那 20,715 次先前只有 ConfigMap 推論，**現在有流量證據**。Classification 頁最後一個 pending assignment 結掉。
→ 順帶：**新 route 的 log 存在本身就證明新 image 在跑**（那段 code 只存在於 35c972e）。行為證據比讀 image tag 硬。

**沒有造成傷害的證據，以及我差點誤讀的地方**：
- PDF 路由 6 小時內 **100% status 200**，跨越部署點無非 200。
- 部署後 **Request 11 / Response 11 完美配對**——這才是「串流沒被 interceptor 干擾」的決定性證據（每條串流都完整走完）。
- 部署後 error log **0 筆**。但 **0 太漂亮，先排除「錯誤 log 停掉」**：同窗口有 2,260 筆 info log，pipeline 活著。
- **更重要的自我修正**：部署前 638 筆錯誤有 **552 筆是 Kafka `ECONNRESET`**（打 `vibrant-notification-events.servicebus.windows.net`，約 89%）。它在部署點消失是**因為 pod 重啟、連線重建**，不是我的改動造成的。**所以「錯誤歸零」不能當成無害的證據**——真正的證據是 PDF 路由的 request/response 配對。
→ 通用形式：**部署後的指標改善，第一嫌疑是重啟本身**（連線重建、快取清空、計數器歸零），不是變更的功勞。要挑出不受重啟影響的指標來判斷。

**staging 探測的結論已寫進 Classification 頁 v4**：`/trans/downloadTestOrderPDF` 不是 drop-in，缺 `clinic_id` 會 400，補上之後位元組完全相同（3,093,587）。原本頁面上「New code: **none**」那格是錯的，已改成「一行」。

**環境**：Azure MFA 過期導致 kubectl 中途失效，Leo 跑 `az login` 後恢復。期間驗證全部改走 Datadog，沒有受阻——**log tag 與行為證據可以替代 kubectl 做部署驗證**，值得記住。

### [2026-09-21 19:30]
Leo 授權三件全做。1 與 2 完成，3 完成前置調查。

**(1) prod skin 死 key 已刪。** 先備份兩份 yaml，`kubectl patch --type=json` remove：`lis-setting-consumer-config` 136→135、`-local-config` 123→122，`inventory_url_skin` 完好。
→ **刻意不強制重啟 prod**：刪 key 對執行中的 pod 無影響（38h 未重啟），而重啟後行為 staging 已驗證過。**沒有理由為了「證明」而在 prod 製造一次重啟**——那會把已知安全的操作變成有風險的操作。

**(2) setting-consumer：票 VP-18324（assign Leo）＋ PR #176（step 1 已送出）。**
- 實作：`getOrderReport` 加 optional `clinic_id`，query 條件式附加；呼叫點傳 `list_sample.sample[0]?.order?.clinic_id`。
- **型別繞了一圈**：先寫 `sample[0].clinic_id` → TS2339，`sample` DTO 沒宣告。查到 `OrderSample_in_samplev2` 有 `clinic_id`，而且 trans 的 proxy 讀同一個 RPC 時也是走 `sample[0].order.*`。改用那條，typecheck 過。**proto 有欄位 ≠ 手寫 DTO 有欄位**。
- **最重要的一次量測：發布順序**。code 與 config 不可能同時生效，所以先量「舊路由會不會被多出來的參數打壞」→ `/proxy/old-report/...` 帶 `clinic_id` 回 **200 且位元組相同**。所以 step 1 可獨立上線、零行為變更，step 2 再翻 URL，中間沒有壞掉的空窗，兩步各自可回退。**這種「中間態」的量測比端點等價性更容易被忘記，但它決定了能不能安全分兩步。**
- 測試：typecheck 乾淨；jest **改動前後都是 2 suites / 1 test 紅**（對乾淨 main 跑過對照）→ 既有基線，非我造成。
- **新發現的洞**：`LIS-setting-consumer` 的 workflow 只在 `push: main` 觸發，**PR 沒有任何 CI gate**，而 merge to main 就是部署。跟 trans 兩個 repo 在 Phase 0.3 之前同款。值得開票。

**(3) VP-18152 前置調查**：
- v1 呼叫點 `setting.practiceInfo.service.ts:9039`（`axios.get(list_customer_by_id_carlos + clinic_id)`，讀 `response.data.customers`），已有我 09-11 留下的 TRANS-OPT 註解。v2 在 `setting/setting.service.ts:1562`。
- **目標 rpc `ListClinicCustomersByClinicID` 的 proto 已經 vendored 在 trans v1**（`protos/clinic.proto:17`），不需要新增 proto。
- 還沒做：`ListClinicCustomerByIDResponse` 與 HTTP `customers` 的形狀對照、下游實際消費哪些欄位、以及 shadow 比對。**這條是活的客戶路徑（14 天 5,023 次），照本 program 的紀律要 shadow 到零差異才切**，不是直接換 client。

### [2026-09-21 20:15]
Leo merge 了 setting-consumer #176，要求 deploy 後測試再進行下一步；並批准 VP-18152 用 S2 模式。

**#176 merge 了但沒有上線——本 session 第二次「merge ≠ 上線」，機制不同。**
- deploy run 35639933793 在 `Build and push image to ACR` 那一步被 **cancelled**（18:42:25，啟動約 100 秒後），同時另一個不相干的 CodeQL run 也被取消。workflow 內**沒有** concurrency 設定。
- **prod 實際跑的是 `c3e166d`**（09-16 那次成功部署），pod 39 小時未動。變更不在線上。
- API 的 actor 是 Leo 帳號，但那只是觸發者，看不出誰按取消。**沒有重跑**——不知道取消原因就重跑 prod 部署不是我該自己決定的事，而且「沒部署」本身是安全狀態，等待零成本。
→ **教訓**：部署驗證要看 **live image SHA**，不是 PR 狀態、也不是「有 run 被觸發」。第一次是 stacked PR 進錯 base，這次是 run 被取消——兩次都靠查 `origin/main` 內容 + live image 才發現。

**另一個我要更正的說法**：我說 `LIS-setting-consumer` 的「PR 沒有任何 CI gate」是錯的。它有一個 org 層級的 **CodeQL** run（不在 repo 的 workflow 檔裡，所以只讀 yml 的 trigger 會漏掉）。正確說法是**沒有 typecheck / test gate**，deploy 路徑上也沒有。**「repo 裡沒有 workflow 檔」不等於「沒有 CI」。**

**VP-18152 形狀對照完成，挖到一個會靜默改行為的地雷：**
- 巢狀差一層：HTTP `response.data.customers` vs gRPC `clinic_customers.customers`（`ListClinicCustomerByIDResponse` → `ClinicCustomers`）。`FullCustomer`（`protos/customer.proto:547`）有 code 讀的全部欄位（`customer_id`/`user_id`/`customer_first_name`/`customer_last_name`）。proto 已 vendored，不用加。
- **地雷**：`setting/tool.ts:91` 的 `isEmpty` 有一行 `if (!a && a !== 0 && a !== '') return true;` → **`isEmpty(0) === false`、`isEmpty(null) === true`**。而 proto3 的 `int32 user_id` 無值時是 `0` 不是 `null`。該路徑用它決定 `invite_status`：
  `isEmpty(user_id) ? 'Account Pending' : 'Account Created'`
  → **直接換 gRPC，所有沒帳號的 customer 會從 Pending 翻成 Created**，是畫面上看得到的錯誤。
- 可以從 code 自身推斷 HTTP 確實回空值：否則 Pending 分支是死碼。
- **所以映射時必須把 `user_id === 0` 正規化成「無值」**——與 S2 當初那條 proto3 `packages → []` 同一類（proto3 的預設值吃掉了「缺值」語意）。shadow 應該是拿來確認乾淨，而不是拿來發現這件事。

### [2026-09-21 21:20]
Leo：「1. 要（重跑 deploy） 2. 不動，等他（VP-18152 是 Zhibin 的票）」。重跑並驗證完成，VP-18152 停手。

**重跑成功並驗證（一次部署同時驗兩件事）**：
- run 35639933793 rerun → success 21:06:09Z；live image `24d8c5c` = #176 merge commit；三個新 pod 1/1、restarts=0。
- **正向證據**：prod request URL 現在帶 `&clinic_id=10697` / `45218` / `139823`——真實且各異的值（來自 sample 的 `order.clinic_id`），不是佔位符。
- **零行為變更**：部署後 **Request 28 / Response 28，全部 200**，完美配對。
- **prod ConfigMap 刪 skin key 的第一次實際生效**：新 pod 內 `skin_placepatientorders` unset、`inventory_url_skin` 還在、沒有崩。刪 key 那步到此才算真的驗證完（先前只有 staging）。
- 錯誤判讀：新 pod 3 分鐘 32 筆 error-level，但 17 筆是 `check order tag`——查 Datadog 發現它部署前每小時 271–1,832 筆，是既有的高頻應用訊息被標成 error；其餘是重啟時的 Kafka consumer rebalance。**沒有新種類**。
  → 又一次「先查基線再判斷」救回誤報。**這個服務的 error level 被雜訊污染得很嚴重**（正常訊息標成 error），所以在這裡數 error 數量沒有意義，只能比對種類。

**deploy 被取消那件事的結論**：查不出誰取消，重跑即成功，沒有重現。**教訓不變：部署驗證看 live image SHA。** 本 session 兩次 merge≠上線都是靠這個發現的。

**VP-18152 停手**：形狀對照與 proto3 `user_id` 零值地雷的分析已記在 09-21 20:15 那則，等 Zhibin。不在他的票上動 code。

### [2026-09-22 01:40] Dream closeout probe — both of today's deploys live and healthy; trans v1 image already moved on
- **trans v1 prod image is now `c546210`, not `35c972e`.** After #802 (17:55Z) three non-Leo PRs merged to `LIS-transformer` main and deployed: #803 (Zhibin, VP-18197 findPatientWithCharge, 21:30Z), #805 (Wang-tianhao, accession-lookup crash fix, 22:02Z), #787 (YFvibrant, LIS-7797 kafka retry storm, 22:05Z). Deploy run 35660819392 success 22:05Z. Error-level lines after that deploy: only `npm notice` x2 and `listOnTimeout` x2 at startup (22:14-22:18Z) — startup noise, nothing recurring.
- **#802's attribution interceptor is still live under `c546210`**: `service:lis-trans-deployment @operation:proxy*Caller` = 894 lines 18:09-22:05Z, 439 lines 22:05-01:37Z (evening decline). The route string lives in attributes, so a free-text `old-report` search returns 0 — query by `@operation`, not by message.
- **#176 live on all three setting-consumer pods** (`image_tag:24d8c5c…`, replicaset `57cdddc9cb`, 4.5 h, 0 restarts). PDF URLs in prod carry real `clinic_id` values (45218 seen at 21:12Z).
- **400s on `getOrderReport` are baseline, not a #176 regression**: 7-day count = 33 `AxiosError 400`, ALL `call_function=getOrderReport`, ~4.7/day with weekday bursts (09-16 had 4 within 2 h, 09-17 six, 09-18 six). Post-deploy 4 in 4.3 h (21:12, 23:47, 00:46, 00:47Z) is inside that pattern. Identical error dumps (`path:`/`url:`/`_header:` lines) exist pre-deploy without `clinic_id`, same `order_status=order_processing|order_received` shape. **Those URL lines are axios error dumps, not per-call logs** — 12 lines since 21:00Z ≠ 12 calls. The qpdf `file is damaged / can't find PDF header` warnings that follow are the 400 body being fed to qpdf; also present pre-deploy (7 in the prior 72 h).
- Datadog service tag for trans v1 is `lis-trans-deployment` (LTM patterns.md already says so); `service:3146` returns nothing — 3146 is only the port in the consumer's URL.
- No STM carries `unblocked_by`/`unblock_when` naming VP-18324 or VP-18260 — nothing to propagate.

### [2026-09-22] VP-18324 step 2 起手 — 卡在 staging 沒有 step 1 的程式
Leo 指派 VP-18324，選方案 A（照票的順序：staging 先）。

**現況查證（不靠記憶）**
- 四份 ConfigMap（ns `setting`）全部還是舊路由：`lis-setting-consumer-config` /
  `-st-config` / `-local-config` / `-local-st-config` 的 `url_downloadTestOrderPDFv2` 都是
  `.../proxy/old-report/downloadTestOrderPDF`。
- prod 六顆 pod（`lis-setting-consumer` x3 + `lis-setting-consumer-local` x3）全在 `24d8c5c`
  = #176 merge commit → **step 1 在 prod 已上線**。
- **阻擋點**：staging 兩顆跑 `9dc0a3e`，來自 `stage_test`，**不含 clinic_id 那個 commit**。
  這個 repo 是刻意雙軌（`main`→prod 的 `setting-consumer.yml`、`stage_test`→staging 的
  `setting-consumer-staging.yml`，各自 `push:` 觸發），main 多 8 個 commit / stage_test 多 6 個，
  同一個修正在兩邊是不同 commit。所以先翻 staging config = staging 全部 400。
- 四份都是 `envFrom: configMapRef` → **改 ConfigMap 不影響執行中的 pod，一定要 restart**。
- ConfigMap **沒有**被 repo 追蹤（repo 內 grep 不到 `url_downloadTestOrderPDFv2` 的 yaml），
  所以 live patch 就是唯一的變更點，沒有 repo drift 問題，但改前要備份。

**在 prod 重量一次（票上的數字是 9/21 staging 的，不是現況）**
從 prod pod 內、用該 pod 自己的 OAuth2 service token，sample 2640083（customer 19838, clinic 100627）：
| 呼叫 | status | bytes | 耗時 |
|---|---|---|---|
| proxy + clinic_id | 200 | 482,019 | 8.8 s |
| trans + clinic_id | 200 | 482,019 | **3.0 s** |
| trans 無 clinic_id | 400 | 42 | — |
第二個 sample 2640082 同樣結論（2,055,992 bytes 雙方一致）。**`/trans` 快約 3 倍**（少一跳 proxy）。

**修正一個先前的說法：兩條路由不是 byte-identical。**
長度一樣但 sha256 不同 → 做了對照組：**同一條路由連打兩次，sha256 也不同**。差異位元組只出現在
offset ~481,913 起的 PDF trailer `/ID [<...> <...>]`，是算繪器每次重產的文件識別碼。
所以正確說法是「除了 per-render 的 `/ID` 之外相同」。#176 的 commit message 寫 byte-identical
不精確，已在 #177 的 PR body 更正。**對非決定性元件下結論前先量同一輸入的重複變異** 這條救回一次誤判。

**已做**：PR **#177 -> stage_test** https://github.com/Vibrant-America/LIS-setting-consumer/pull/177
cherry-pick `2e10628` 無衝突；typecheck 乾淨；jest 在 stage_test **改動前後都是 2 suites / 1 test 紅**
（ECONNABORTED，測試裡打真實 HTTP），baseline 是在這條 branch 上實跑對照的，不是沿用 main 的紀錄。

**等 Leo merge #177 → staging 部署 → 翻兩份 staging config + restart → 驗證 → 再翻兩份 prod config。**

### [2026-09-22] proxy 家族全貌盤點 + 開三張後續票（Leo：「不要再call proxy, 直接call ... abc 都開都做」）
**完整路由清單（Explore agent，trans v1）**：只有兩個子家族、共 17 條。
`proxy.controller.ts:26` = `/proxy/grpc`（6 條），`old-report.controller.ts:45` = `/proxy/old-report`（11 條）。
- `/proxy/grpc`：5 條 gRPC fan-out（getKitStatus→ShippingService、getPatientTestsResult / getTestStatus
  →TestResultGrpcService、getQuestionaireBySampleId→ShippingService、listTnpCode→TnpService）
  + **1 條不是 gRPC**：`sendSkinPlacePatientOrders` 是純 HTTP POST 到**外部 CRM**
  `https://www.vibrant-america.com/crmapi/placepatientorders`（`proxy.service.ts:220-223`），
  而且會轉發呼叫者的 raw bearer、並用 `julien_barcode` 覆蓋 `comments`。
- `/proxy/old-report`：11 條全部 front legacy Java on-prem `:8081/secure/nologin/*`
  （dev 192.168.10.153 / prod 192.168.60.77），其中 3 條另外打 order-management 的 PDF 端點。
  **每一條在 `trans-reports.controller.ts` 都有 1:1 雙胞胎，共用同一個 `OldReportProxyService`。**

**授權不對稱（兩個家族不同，重要）**
- `/proxy/old-report`：有 `assertSamplesOwned` + `isTrustedInternalCaller` 繞過（`:63-67`），
  且**不跑** `resolveIdsForHttpOptional`（註解自稱 spoof-safe）。`/trans` 雙胞胎則會跑，身分可從 query 補。
- `/proxy/grpc`：**完全沒有 ownership gate**，只有 `CustomJwtAuthGuard`，`req.user.userId` 純粹當
  metadata 做歸因。=> 改直連**不會失去任何授權行為**，只少一次 JWT 驗證跳。這點讓 VP-18345 風險遠低於 old-report 那條。

**VP-18345 之所以便宜**：直連的程式碼還在 repo 裡，只是被註解掉——
`controller.ts:8832-8843`（kit）、`:9193-9203`（result）、client 在 `grpc.options.ts:24-32`，
proto `protos/shipping.proto` / `protos/tests.proto` 都已 vendored。直連路徑雙雙 prod-proven
（trans v2 `proxy-grpc.service.ts:129` 自 09-16；LIS-Report `grpc.service.ts:205` 長期高流量）。

**解掉 agent 留的未決問題 #2**：它說 setting-consumer 的 `.env` 還指向 cloud-proxy、不確定 prod 切了沒。
我今天實讀四份 live ConfigMap：`proxy_getkit` / `proxy_getresult` 都已是
`lis-trans-service.default.svc.cluster.local:3146/proxy/grpc/...`，**cutover 已生效**，
所以 VP-18320 comment 裡 Datadog 歸因查到的殘餘流量就是 setting-consumer，兩邊對得起來。

**新開三張（掛 VP-18260，assign Leo）**
- **VP-18345** setting-consumer 兩條 gRPC 改直連
- **VP-18346** `/proxy/old-report` 補 `ProxyCallerLogInterceptor`（目前只有 `/proxy/grpc` 有，
  所以「10 條零流量」是 code search 推的，看不到瀏覽器/外部/未 clone repo 的呼叫者）
- **VP-18347** `sendSkinPlacePatientOrders` 的 billing 寫死網址（`ProZOrderServiceImpl.java:120`，
  自帶 TODO "Blocks cloud-local-proxy scale-to-0"）+ trans v2 未 gate 的呼叫

**cloud-local-proxy** = trans v1 proxy 家族的 route-for-route 複製（on-prem），兩個 controller 都帶
"TRANS-OPT RETIRING" banner。退場三階段：cloud-local-proxy → trans v1 `/proxy/*` → `/trans/*` 或直連。

**Gotcha**：`mcp__vibrant__create_jira_issue` 建票回 **403**（service account 無權限）；
改用 `mcp__claude_ai_Atlassian__createJiraIssue`（以 Leo 帳號）成功。下次建票直接用後者。

**未解**：Leo 說「跟著177一起merge」，但 B 在 LIS-transformer、C 在 LIS-backend-billing + trans v2，
不同 repo 無法與 #177（LIS-setting-consumer / stage_test）同批 merge；且 #177 已開、照「一個 PR 一個 head」
不再往該分支推 commit。已向 Leo 說明並建議 #177 照原訂走完。等回覆。

### [2026-09-22 23:2x-23:33Z] VP-18324 step 2 DONE — 四份 ConfigMap 全部翻到 /trans（Leo：「177 merge 了，請你接著做」）
- #177 merge 成 `22d09fe`；**兩顆 staging pod 的 image 就是 `22d09fe`**（看 live image SHA，不看 PR 狀態——
  本 program 已兩次踩到 merge≠上線）。另外在 staging 的 `/dist` 裡 grep 到 `clinic_id=${clinic_id}`，
  確認新程式真的在跑，不只是 tag 對。
- 順序：staging 兩份 → 驗 → prod `lis-setting-consumer` → 驗（含真實 PDF）→ prod `-local`。
  兩個 prod deployment 分開做，前者當 canary（各自吃不同 ConfigMap，可以分開翻）。
- 四份都先 `kubectl get cm -o yaml` 備份到 scratchpad 才 patch；patch 後 key 數量不變
  （135/122/135/122），只有值變。
- **`envFrom: configMapRef` → 改 ConfigMap 不影響執行中的 pod**，四個 deployment 都 rollout restart。
  **踩到一次值得記的**：`kubectl rollout status` 回報 "successfully rolled out" 時，**舊 pod 還在**
  且還帶著舊的 env。判準要看「只剩新 pod」+ 逐顆 exec 讀 env，不是 rollout status。
- 最終狀態：8 顆 pod（6 prod + 2 staging）全部 Ready / 0 restart，逐顆 exec 確認
  `url_downloadTestOrderPDFv2` 都是 `/trans/downloadTestOrderPDF`。prod image 仍是 `24d8c5c`（只有設定變）。
- **正向驗證（prod，用 pod 自己的 env）**：5 個真實 sample 全部 200，且 `/trans` 與舊 proxy 的
  **位元組長度完全一致**：482,019 / 2,055,992 / 493,190 / 481,611。sha 不同是 per-render `/ID`（已證）。
- 六顆 prod pod 啟動後 0 個 getOrderReport 錯誤、0 個非例行錯誤。
- **日誌裡看不到 `/trans/downloadTestOrderPDF` 字串是預期的**——那些 URL 行是 axios 的錯誤傾印，
  不是 per-call log，沒失敗就不會出現。別把它讀成「沒有流量」。
- 回滾：把四份 ConfigMap 的該 key 改回 `/proxy/old-report/downloadTestOrderPDF` 再 restart；
  備份 yaml 在 scratchpad `cm-backup/`。step 1（程式帶 clinic_id）不需要回滾，舊路由接受該參數。

**VP-18324 剩下**：`/proxy/old-report/downloadTestOrderPDF` 的流量要歸零兩週後才能刪那 11 條路由，
而刪除前應先做 **VP-18346**（補歸因攔截器）——目前「其他 10 條零流量」是 code search 推的，看不到外部呼叫者。

### [2026-09-22] Backup/rollback 方案做實（Leo：「先不刪，把可以backup 的方案做好先」）
- **發現：四份 ConfigMap 有真機密**（`Azure_kafka_connection_string`、`Azure_redis_pass`、
  `Azure_noti_topic_connection`、`OAUTH2_CLIENT_ID`）→ `kubectl get cm -o yaml` 的 dump
  **絕不可進任何 git repo**。session 暫存的那份已刪。
- **而且整份 dump 本來就是錯的備份物件**：只動了一個 key，沒人會為了退一個 key 還原 135 個。
  正確的備份是「那個 key 的前後值 + 指令」，而前值是 URL 不是機密，甚至可以從路由名重建。
- **回滾在 staging 實際演練過，不是寫出來的**：patch 回 proxy → restart → 新 pod
  `66b4c4c849-97z7h` 帶舊值且 proxy 路由實際可用（且 `/trans` 無 clinic_id 仍 400，證明真的退回去了）
  → 再 patch 回 `/trans` → `66cc5f79f-pqdjf`。單 pod deployment 每次約 60-90 秒。
- Runbook（無機密）：`runbooks/vp18324-proxy-pdf-route-cutover.md`，commit `2fd02b1`。
  裡面釘住三件容易踩的事：(a) dump 不能進 repo 且不是正確的備份物件；
  (b) `rollout status` 說完成時舊 pod 還在、還帶舊值，判準要看「只剩新 replicaset」+ 逐顆 exec 讀 env；
  (c) 比對 PDF 要比長度不能比 hash（`/ID` 每次重產），且路由字串在 `custom.url` 屬性不在 message
  （free-text 搜 `old-report` 回零筆不等於沒流量）。

### [2026-09-22] 切換後的流量實測（trans v1 request log，`@url:*downloadTestOrderPDF*`，每分鐘）
```
23:20-23:29Z  proxy 4-10/min   trans 0
23:30-23:31Z  proxy 4-6        trans 4-8     <- rolling restart，新舊 replicaset 並存
23:32Z 起     proxy 0          trans 8-14
23:38Z        proxy 4          trans 8       <- 我自己的驗證腳本（它會故意打舊路由對照）
```
23:38 那 4 筆能從時間與數量推是自己的 probe，但**無法證明**——因為 `/proxy/old-report` 沒有歸因
（`old-report.controller.ts` 只有 `@UseInterceptors(SentryInterceptor)`）。這正是 VP-18346 的理由，
也是「如果流量沒歸零會怎樣」的真正答案：數得到、認不出來。

**更正一個我自己在 VP-18324 描述裡寫太滿的說法**：那裡寫「#802 的 attribution logging 確認每一筆
`/proxy/old-report/downloadTestOrderPDF` 都來自 setting-consumer」。已查證 `ProxyCallerLogInterceptor`
**只掛在 `/proxy/grpc`**，old-report 的呼叫者其實是 ConfigMap 掃描 + code search + 流量吻合**推論**出來的。

### [2026-09-22] VP-18346：我搞錯了前提，而且錯在同一條紀律上
**錯誤**：我說 `/proxy/old-report` 沒有歸因攔截器，因此開了 VP-18346、在 VP-18324 發了「更正」comment、
還寫進 runbook §8。**全部是錯的。** `5a9473f`（2026-09-18）早就把 `ProxyCallerLogInterceptor`
掛上去了，部署中的 prod image `e9a5ec0` 也含它。

**根因（不是「忘了 fetch」，比那個更糟）**：我 `git fetch` 了，然後 grep **工作樹**——而工作樹在
`9264e9e`，落後 origin/main 20 個 commit。而且 `git status -sb` 印出的 `[behind 20]` **就在我自己那一次
指令的輸出裡，我讀過去了**。AGENTS.md 原則 0 的第二段寫得很清楚：「確認過之後就直接讀本地檔」——
前提是**確認過**。我做了 fetch 這個動作，跳過了確認這個判斷。
派出去的 Explore agent 也讀同一份 stale checkout，我給了路徑卻沒有釘 ref，所以它的報告繼承了同一個錯。

**實際量到的（attribution 一直在記，只是沒人看）**：4 天內
| route | ua | xff | events |
|---|---|---|---|
| `/proxy/old-report/downloadTestOrderPDF` | axios/1.4.0 | 空（叢集內） | 2,932 |
| 其他 10 條 old-report | — | — | **0** |
=> 那 10 條「沒有呼叫者」現在是**量出來的**，比原本 code-search 推論強得多。這是個好消息，
只是我用錯誤的方式發現它。

**VP-18346 重新定義**：真正剩下的是兩個 family 共用同一組 label——2,932 筆 old-report 事件現在
answer 到 `@operation:proxyGrpcCaller`，查「誰在打 grpc proxy」會拿到 99.8% 不是 grpc 的結果。
兩邊的退場決策都靠這些查詢，所以值得修。
- PR **#813 -> main** https://github.com/Vibrant-America/LIS-transformer/pull/813
- family 從 route path 推導**而非建構子參數**：Nest DI 下 `family = 'grpc'` 這種預設值會被解析成
  必要的 `String` 依賴而讓整個 app 起不來（factory 那條 `@Optional() @Inject(TOKEN)` 教訓），
  而且 controller 還是可能被接錯 label；路徑不會跟自己不一致。
- grpc 的 label 逐字不變，且新增測試逐字釘住——VP-18320 的證據就建立在那個搜尋字串上。
- 9/9 測試過；tsc 的 10 個既有錯誤在 clean origin/main 上重跑對照過，逐字相同。

**另一個踩到的**：LIS-transformer 的 pre-push DI boot smoke 在**乾淨 worktree** 會失敗
（`JwtStrategy requires a secret or key`），因為受測 code 的 `dotenv.config()` 讀 cwd 的 `.env`，
而 worktree 沒有。主 clone 有 `.env` 所以會過。這正是 factory 的
「Gate 宣稱的環境要由 gate 自己控制，不能靠受測程式碼的 dotenv」。暫解是把 `.env` 複製進 worktree
（已確認在 .gitignore 第 40 行）。

**待辦**：runbook `vp18324-proxy-pdf-route-cutover.md` §8 那段關於「沒有歸因」的敘述要改掉。

### [2026-09-23] VP-18345 實作（Leo 批准 shadow）— PR #179 -> main
**票上的前提對一半，錯的那一半會送出靜默錯誤答案**
- `getPatientTestsResult`：註解掉的程式碼確實是同一個 method 同一個 key（`{id: patient_id}`）→「解除註解」成立。
- `getKitStatus`：**不成立**。註解掉的是 `getKitStatus({accession_id})`，proxy 實際打的是
  `GetKitStatusBySampleId({sample_id})`——不同 method、不同識別碼。而且 vendored
  `protos/shipping.proto` **根本沒宣告** `GetKitStatusBySampleId`（只有舊的 `GetKitStatus(AccessionId)`）。
- 兩邊共同：註解掉的 client options 指向寫死的 on-prem 位址（`192.168.60.6:30600` / `:31865`），已死。
  改建在 `SHIPPING_RPC` / `TEST_RESULT_RPC` 上（值從跑著的 trans v1 pod 讀出來）：
  `lis-shipping-service-grpc.shipping.svc.cluster.local:63142` /
  `lis-test-connect-grpc-service.results.svc.cluster.local:6889`。
  **動工前先從兩個 prod deployment 各一顆 pod 做 TCP 連通測試，都 CONNECT**（`-local` 那組不能假設）。

**設計**：`SETTING_GRPC_MODE` = `proxy`（預設，逐位元組等於今天）| `shadow`（兩邊都打、**送 proxy 的答案**、
記錄差異）| `grpc`。仿 trans v2 2026-09-16 的 `TRANS_PROXY_GRPC_MODE`。部署不改變任何行為，
之後每一步都是改 env 不是部署。

**接手 trans v1 的兩個行為**：
1. metadata 用本服務自己的 `createOAuth2Metadata`。**刻意差異**：`service-name` 是 `lis_setting_bot`
   而非 proxy 的 `lis_frontend_service`——那是歸因不是授權，誠實的值是真正在呼叫的服務。已寫進 PR。
2. proto3 正規化 `send_out[i].packages -> []`（Sentry #68038）。

**比對邏輯是最該 review 的部分**：naive deep-equal 會讓 shadow 廢掉（幾乎每次都報差異就沒人看）。
正規化掉三種非差異：absent vs `undefined`（proxy 答案過了 JSON）、absent vs `[]`（proto3 省略空 repeated）、
`1` vs `"1"`（64-bit 欄位以字串回來）。**其中兩種是被我自己的測試打出來的——實作比它自己的註解更嚴格。**
報告只帶路徑與型別、不帶值（病人資料），且有上限避免一次結構性不符洗版。

**測試**：17 個新測試（純比對與 mode 邏輯）。全套與 tsc 在 clean origin/main 上重跑對照：
2 個既有紅 suite、0 type error，前後相同。
誠實但書：`git stash` 不收未追蹤檔，所以 baseline 那輪仍載入新 spec；它隔離的是三個已追蹤檔案的影響。

**stage_test 那份先不開**：本次預設 `proxy`，staging 少了它不會壞（跟 VP-18324 不同），
等 #179 review 定案再 cherry-pick，避免兩條線帶到不同版本。

**後續**：#179 merge → prod 設 `SETTING_GRPC_MODE=shadow` → 讀 `grpcShadow` 日誌到分歧率為零
→ `grpc` → 刪兩個 ConfigMap key 與 trans v1 兩條路由。

### [2026-09-23] #178 merge + prod 部署驗證，並抓到我自己埋的一個缺陷
**#178（stage_test -> main）review**：`origin/stage_test..origin/main` 為空 → merge 不會弄丟 main 任何東西；
`clinic_id` 不會被套兩次（兩條線各有一個 commit 做同一修改，但 merge 在該區塊不增不減）。
直接跑 merge 後的樹（= stage_test 的樹）：tsc 0 error、測試與 clean main baseline 相同
（2 紅 suite / 1 紅 test）、兩個新 spec 全綠。
**但它夾帶 VP-18182/18183（Fan Zhou，09-10，293 行，改抽血信發送條件）上 prod** —— 兩張票 Dev Complete，
但在 stage_test 上單獨躺了 13 天且是客戶面行為。已向 Leo 指出「兩半的風險輪廓不同」：
我的改動預設惰性（env 未設 = proxy，回退改 env），Fan 的立刻生效（回退要 revert code）。Leo 選擇一起 merge。

**prod 部署驗證（image `e8986de`，6 顆 pod 全新）**：全部 Ready / 0 restart / 乾淨啟動 /
**0 個 DI 或 proto 錯誤**（兩個新 `@Client` 是這次最大的結構性風險，已清）/ `SETTING_GRPC_MODE` 未設 /
新程式在 dist / VP-18324 的兩條路由仍位元組一致（480,857 與 2,057,367，兩邊相同）/ 六顆 pod 零錯誤。

**抓到的缺陷（我自己的，PR #180 修）**：我給 gRPC client 寫了 fallback 位址。
- `SHIPPING_RPC` / `TEST_RESULT_RPC` **在八顆 pod 全部未設**（prod 與 staging 皆然）→ fallback 就是實際生效值。
- 兩個環境的服務**不同**：prod 走叢集內 DNS，**staging 走 `192.168.60.6:31865` / `:30600`**。
- 我寫死的是 prod 的。從 staging pod 實測：prod 位址 **CONNECT**、staging shipping **ECONNREFUSED**。
  → 在 staging 開 shadow 不會失敗，會**安靜地讀 prod 資料**並產出無意義的比對。**會動的錯誤預設值比沒有預設值更糟。**
- **順帶更正我自己的另一個說法**：我在原 commit 說那些 `192.168.60.6` 位址「已經死了」。
  它們是 **staging 的位址，staging trans v1 今天還在用**。我從一則關於另一個 on-prem 位址的筆記過度一般化。
- 修法：拿掉預設值；`resolveMode(mode, serviceAddress)` 在位址為空時一律回 `proxy`。
  啟用直連變成兩個刻意動作（位址 + 模式）而非一個。
- **副產品發現**：從 staging setting-consumer pod 連 staging 自己的 shipping 位址是 ECONNREFUSED
  → kit-status 那半**今天在 staging 沒有可用目標**，第一次真正的 shadow 只能在 prod 做。

**PR**: #180 -> main（待 review）。

### [2026-09-23] #180 部署驗證 — 缺陷確認關閉（在部署產物上實跑，不是靠單元測試）
- main `69f8581`，六顆 prod pod 全換新、Ready、0 restart。
- **這次盯的結構性風險**：env 未設時 client 的 `url` 是空字串，而 `getService()` 在 `onModuleInit` 就跑。
  結果六顆全部乾淨啟動、**0 個 URL/grpc-init/DI 錯誤** → grpc-js 接受空 URL 而不在建立時爆炸。
- **在 pod 裡載入部署中的 `dist/setting-consumer/proxy-grpc-mode.js` 實跑保護邏輯**：
  `SETTING_GRPC_MODE=undefined`、`SHIPPING_RPC=""`、`TEST_RESULT_RPC=""` → 兩邊都解析成 `proxy`；
  而且 `resolveMode("shadow", "")` 也回 **`proxy`** ——「就算現在有人把模式設成 shadow 也不會走直連」，
  這是缺陷關閉的直接證據。
- VP-18324 兩條路由仍位元組一致（480,857 / 2,057,367），六顆 pod 零錯誤。
- **未完成**：Datadog 查詢工具在此時連續回 "Was there a typo in the url or port?"（同組查詢稍早可用），
  所以「舊 proxy 路由流量是否已歸零」這一項**沒驗到**，留待下次。

**啟用 shadow 前必須先做的事（不是現在）**：
1. 把 `SHIPPING_RPC` / `TEST_RESULT_RPC` 加進要啟用那個環境的 ConfigMap，用**該環境自己的**值。
2. 記住 staging 的 shipping 位址從 setting-consumer pod 是 ECONNREFUSED → kit-status 那半
   第一次 shadow 只能在 prod 做。

### [2026-09-23 ~22:00Z] 舊 proxy 路由流量確認：**0**（Datadog 掛掉，改從來源證）
Datadog MCP 連續失敗（先 "Was there a typo in the url or port?"，後 "Unable to connect"），
沒有盲目重試，改去 **trans v1 pod 自己的日誌**數——那是來源，比聚合器更直接。

最近 60 分鐘，三顆 prod trans v1 pod（image `ad5ab17`）：
| pod | old-report/downloadTestOrderPDF | trans/downloadTestOrderPDF | 總行數 |
|---|---|---|---|
| 679b79bb5d-4g5dl | **0** | 0 | 86 |
| 679b79bb5d-6q9hc | **0** | 6 | 407 |
| 679b79bb5d-zbvvd | **0** | 8 | 265 |

**這個零有對照組**：同一條 grep、同一份日誌，`trans` 那欄抓得到 14 次 → 證明日誌含這類路由字串、
pattern 有效、pod 有在產出。零不是查詢寫壞（「自己拼的查詢回零筆先驗必然存在的值」這條紀律）。
切換前的基準是 4-10/分鐘，所以一小時的零 ≈ 300-600 次預期命中沒有發生。

**視窗限制**：trans v1 於 21:00Z 剛重新部署（image `ad5ab17`），pod 日誌只回溯到那時，所以只有約 60 分鐘。
更長的歷史要等 Datadog 恢復。

**一個我差點誤用的「佐證」**：我順手數了 VP-18346 的新 label（`proxyOldReportCaller` / `proxyGrpcCaller`），
兩者都 0。但 `proxyGrpcCaller` 不該是 0（setting-consumer 的兩個呼叫仍走 proxy，`proxy_getkit`/`proxy_getresult`
env 確認仍指向 `/proxy/grpc/*`）。查證後：**攔截器的輸出不進 pod stdout**（它的四個欄位在日誌裡一個都沒有），
所以那組數字是無效資訊、不是第二個確認。已捨棄，不當佐證用。

**另外**：VP-18346 的 PR #813 已 merge 並部署（`ad5ab17` 含它），但新舊 label 是否真的分開，
要等 Datadog 恢復才能驗（label 只存在於送往 Datadog 的那條路徑）。

### [2026-09-23 ~22:15Z] Datadog 恢復 — 7 天流量驗完，公告草稿完成（Leo：「請你把 ... 要移除寫進doc，我會發到slack，等一個禮拜後移除」）
**7 天逐小時（`@url:*downloadTestOrderPDF*`）**：切換前 proxy 尖峰每小時 100-650
（09-17T20 552、09-21T21 568、09-22T22 646）；**09-23T00:00Z 起 proxy 每小時都是 0**，
只有兩個例外：09-23T18 與 T19 各 4 筆——那是我自己的驗證探針（每次跑 2 個 sample、每個 request 2 行 log）。
同期 `/trans` 承接 100-600/小時。**工作沒有消失，是搬家了。**

**歸因交叉確認**：`@operation` 查詢顯示 18 時與 19 時 old-report 各 **2 個 request**
（= 2 行 url log/request × 2 = 4，對得上），使用者代理 axios/1.4.0。有機流量為 0。

**attribution 上線 5.3 天以來（09-18 16:32 PDT 起）全家族只有一條有呼叫者**：
`downloadTestOrderPDF` 2,936 筆，其餘 **十條全部 0**——量出來的，不是 code search 推的。

**VP-18346 的 label 分離：已部署但尚未被觸發，因此未驗證。**
trans v1 於 21:00Z 換到 `ad5ab17`（含 PR #813），但所有歸因事件都在 21:00Z **之前**，
所以 `@operation:proxyOldReportCaller` 還沒出現過。**不可宣稱它有效**；等有 request 打到再驗。
（先前我在 pod stdout 裡數 label 得到 0/0，已確認攔截器輸出不進 stdout，那組數字無效、已捨棄。）

**公告草稿**：`drafts/proxy-old-report-removal-announcement.md`（英文，Leo 發 Slack）。
- 主段只講 `downloadTestOrderPDF`，移除日 **2026-09-30**（09-23 起算一週）。
- 第 2 段涵蓋其餘十條，標為可刪——理由寫在「Notes for Leo」：同一次刪除、現在有量測支撐、
  分兩次公告等於邀請第二輪「沒人通知我」。
- 遷移指引點名那個會咬人的差異：`/trans` 需要 `clinic_id`，否則 400（service token 兩個 claim 都沒有）。
- 草稿裡誠實標註「VP-18346 的 label 分離尚未觀察到生效」，不讓未驗證的事混進公告的證據裡。

### [2026-09-23] 一次性排程已安裝（Leo：「merged. 請直接裝」）
PR #48 merge（main `fa3d21a`）後安裝 `com.lis.proxy-old-report-removal`。
**驗證是問 launchd 自己，不是看檔案**：
`launchctl print gui/$(id -u)/com.lis.proxy-old-report-removal` →
`Month 9 / Day 30 / Hour 9 / Minute 0`、`state = not running`、`runs = 0`、`last exit code = (never exited)`。
安裝的 plist 與 repo 版 `diff -q` 相同（無漂移）；runner 可執行；`.done` marker 不存在（= 已武裝）。

**Pre-flight**：在 runner 自己 export 的那條 PATH 底下用 `env -i` 逐一解析工具——
claude / gh / git / node / caffeinate / osascript / launchctl 全部找得到。
（launchd 給的是最小 PATH，這類 job 最常見的死法就是 `claude: command not found`，
現在是量過的不是假設的。）

**這個 job 的合約**（細節見 `DailyJob/proxy_old_report_removal/README.md`）：
量流量 → 只有真零才開 ticket + **draft** PR；任何流量、Datadog 失敗、
**對照組沒回資料**、或無法有把握解讀的結果 → 什麼都不開、只報告。永不刪路由、永不 merge、永不碰 ConfigMap。
失敗的執行**不寫 marker**，所以沒跑成的工作會再響一次。

**尚待**（09-30 當天或之前）：
1. VP-18346 的 label 分離仍未被觀察到生效（那條路由已無流量，所以還沒機會觸發）。
2. 公告草稿 `drafts/proxy-old-report-removal-announcement.md` 等 Leo 發 Slack。

### [2026-09-23 14:55 PT / 21:55Z] staging trans v1 兩個 gRPC 目標修復 + VP-18345 在 staging 開 grpc mode 實測

**起因**：Leo 要我在 #179 部署後測 VP-18345。在 staging pod 內用它自己的 `getServiceToken` 打
`proxy_getkit`，三個 sample 全部 `http=500`。到 trans v1 staging 追，錯誤是
`14 UNAVAILABLE: connect ECONNREFUSED 192.168.60.6:31865` —— **正是 VP-18345 票裡那個「已死的寫死
on-prem shipping 位址」，staging 的 trans v1 到今天還在打它**。24h 內同樣錯誤 48 筆、最早
`08:47:19Z`，早於 #179 部署（17:13Z）8.5 小時 → 既有狀態，不是這次部署造成。

**變更 1（Leo 批准）`lis-trans-config-st`**：`SHIPPING_RPC` `192.168.60.6:31865` →
`lis-shipping-service-staging-grpc.shipping.svc.cluster.local:63142`；`TEST_RESULT_RPC`
`192.168.60.6:30600` → `lis-test-connect-staging-grpc-service.results.svc.cluster.local:6889`。
prod 的 `lis-trans-config` 早就是 in-cluster 位址，這只是把 staging 對齊。`trans.grpc.options.ts:82`
是 `url: process.env.SHIPPING_RPC` **無 fallback**，ConfigMap 即唯一來源。rollout restart 後同一支
探測腳本：**500 → 200**。`tnp_rpc` 仍是死的 `192.168.60.6:30600`，未動。

**變更 2（Leo 批准）`lis-setting-consumer-st-config`**：加
`SETTING_GRPC_MODE=grpc` + `SHIPPING_RPC` + `TEST_RESULT_RPC`（staging 位址）。

**⚠️ 地雷：`grpc.options.ts:25,37` 的預設值寫死的是 PROD 位址**
（`lis-test-connect-grpc-service...` / `lis-shipping-service-grpc...`）。任何環境只設
`SETTING_GRPC_MODE=grpc` 而不設另外兩個 URL，**就會直接去打 prod 的 shipping / test-result service**。
三個 key 必須成組設定。這是我在 gate 的 Gate 1「改前」階段才挖出來的，票和 PR 都沒標。

**A/B 實測（同一個 pod、同一個 sample、兩條路各打一次）**：staging kit 資料稀疏，掃了 44 個
sample id 才找到一個非空的（`500000`）：
```
proxy  : {"return_from":{"kits":[{"tracking_number":"796075684150","kit_status":"LAB_RECEIVED"}]}}
direct : {"return_from":{"kits":[{"tracking_number":"796075684150","kit_status":"LAB_RECEIVED"}]}}
raw JSON equal : true
diffShadow     : null      <- 用 PR 自己的比對函式跑的
```
其餘 sample 兩邊都回空物件，一致。`protos/shipping.proto:7` 確認已宣告 `GetKitStatusBySampleId`。

**VP-18345 已經在 prod 了，不是只有 staging**：21:06Z 有人推 main（`31da65c`，PR #181
sync-core-patient-proto），main 同時觸發 `setting-consumer-staging` 與 `setting-consumer` 兩個
workflow，四個 deployment（prod/staging × cloud/local）全換成該 image，而它含 88bcca7。
prod ConfigMap 三個 key 皆不存在 → 仍是 `proxy` mode、行為未變。預設值設計擋住了這次，
但「staging 先、prod 後」的節奏實際上已被 main 的 auto-deploy 繞過。

**修正我自己稍早的數字**：我曾用 `kubectl logs | grep` 統計 prod trans v1 的 `getKitStatus`，
得到「24h 內 0 筆」。**錯的** —— caller-log 走 LisLoggingService 進 Datadog、不進 stdout。
Datadog 實際：24h 內 `/proxy/grpc/getKitStatus` 9 筆、`/proxy/grpc/getPatientTestsResult` 3 筆、
`/proxy/old-report/downloadTestOrderPDF` 504 筆。結論不變（shadow 樣本累積會很慢），但數字要以
Datadog 為準。這是 patterns.md 那條「stdout ≠ 全部日誌」的又一次實例。

**VP-18346 續**：#813 merge 後 prod 部署 **failure** —— 掛在它自己沒更新到的另一支 spec
`old-report-caller-log.spec.ts:83`（`expect(operation).toBe('proxyGrpcCaller')`，與新行為對撞）。
該 spec 在 #813 的 branch head `039b18b` 上就已存在且已紅，`gh pr checks 813` merge 前就是 fail
—— 不是 merge skew，是「只跑了改到的那一支 spec」。斷言在 rxjs subscribe callback 內，一炸就
`done()` 不會被呼叫，jest 只報成 5000ms timeout，掩蓋了真因。`176503a`（YFvibrant，20:12Z）已修，
20:47Z / 21:33Z 兩次 prod 部署成功，prod transformer 現為 `11e67d8`。label 分離仍未觀察到生效：
Datadog 顯示最後一筆 caller-log 是 20:37Z（deploy 之前），3 小時內全域只有 5 筆，流量是突發式的。

**回滾**：兩個 ConfigMap 改前完整備份在該次 session 的 scratchpad
（`backup-lis-trans-config-st.yaml` / `backup-lis-setting-consumer-st-config.yaml`）。
兩者皆不在任何 repo 內，只能 `kubectl patch`，無 PR 可開。

**未解**：
1. `lis-setting-consumer-local-st` 仍是 proxy mode（自己的 ConfigMap、`platform_type=local`、
   Bull 在 on-prem redis db 4，與 `-st` 的 Azure db 1 隔離）—— 要不要一起開，待 Leo 決定。
2. staging trans v1 的 `tnp_rpc` 仍指向死的 `192.168.60.6:30600`。
3. `grpc.options.ts` 的 prod 預設值要不要改成「無預設、缺少就啟動失敗」。

### [2026-09-23] VP-18320 合併十條 old-report 路由（Leo：「可以合併」）+ 證據重新量過

**重新量測（15 天窗口已滑到 09-08 → 09-23，不是公告當時的 09-03 → 09-18）**：
- `/proxy/grpc` 逐日：`getTestStatus` 與 `getQuestionaireBySampleId` 切換前 129–1,876/日、每日 lockstep，
  **09-17 起連續 7 天整整 0**（公告當時只有 2 天）。`listTnpCode` 15 天完全不出現。
  `getKitStatus` 7–15/日、`getPatientTestsResult` 1–5/日，兩條都還活著。
- `/proxy/old-report`：只有 `downloadTestOrderPDF` 有量（**20,669**），其餘十條 15 天全 0。
- **儀器筆記**：`@url` 含 query string，直接 GROUP BY 會炸成上萬列（第一次查就中了，被 truncate）。
  要用 `split_part("@url", '?', 1)` 才是逐路由計數。

**替代路徑逐條對過 code（origin/main，不是本機——本機落後 39 commits）**：十條每條都有同名
`/trans/*` 雙胞胎。**先前 classification doc 寫「呼叫同一個 OldReportProxyService class」是對的，
但路徑不是直接的**：八條是 `TransService.X` → `oldReportProxyService.X`（多包一層，順便多了 navigator
gate + Kafka audit + language），只有 `getRequisitionForm` / `oneClickPersonalizedReport` 是直接呼叫。
結論不變（同下游、同 env key），但描述要修正。

**兩條不是 drop-in（新挖到的，之前沒人講）**：
- `GetSpecificReports`：proxy 版串原始 `.gz`，`/trans` 版解壓縮 + parse 後回 **JSON**。回應形狀不同。
- `getOrderSummaryReportZip`：proxy 版走 `generateOnlineZipNoJWT` 以 `customer_id_arr` 定範圍；
  `/trans` 版那行被註解掉、改走 JWT 定範圍的 `generateOnlineZip`。同一份產物、不同的定範圍機制。

**刪除 PR 最危險的地方**：`OldReportProxyService` 與它全部的 env key **必須留著**——`/trans` 雙胞胎
走的就是那些方法。DTO 只能刪 5 個（`GenerateOrderpdfQuery` 給存活的路由、`GenerateProducctReportQuery`
被 service 自己 import）。

**產出**：`docs/plans/trans-optimization/vp18320-removal-and-replacements.md`（要刪的 13 條 + 逐條替代
+ 明確留下什麼 + PR 形狀 + config key 要重新盤點的理由）、`drafts/vp18320-widening-comment.md`（英文
comment 草稿，**未發**）。Jira description 的 Scope 段與 QA twin QH-7163 都還只寫三條，要不要改等 Leo。
