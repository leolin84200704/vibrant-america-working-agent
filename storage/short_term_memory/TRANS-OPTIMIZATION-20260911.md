---
id: TRANS-OPTIMIZATION-20260911
title: Trans v1/v2 optimization program — planning phase (no ticket yet; related epic
  VP-17348 / VP-18152)
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
updated: 2026-09-14
links:
- INCIDENT-20260518
- INCIDENT-20260601-sftp-hang
- INCIDENT-20260910-emr-v2-di-crashloop
- QH-1104
- QH-1130
- QH-1159
- QH-1591
- QH-1775
- QH-211
- QH-2259
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
- VP-17422
- VP-17714
- VP-17753
- VP-17766
- VP-17825
- VP-17868
- VP-17870
- VP-18048
- VP-18050
- VP-9299
- business-model
- failures
- repo-catalog
- repos
score: 0.63
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
