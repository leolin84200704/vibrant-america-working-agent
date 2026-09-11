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
updated: 2026-09-11
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
- `cloud-local-proxy` repo not local; its non-trans callers unknown (meeting mentioned a legacy report caller from on-prem).
- The front end that calls cloud-local-proxy directly is not va-portal / vibrant-wellness-portal / pns-portal (0 references); unidentified.
- STM `_index.md` last updated 2026-09-03 (>3 days) → dream pipeline possibly stalled; reported to Leo.

# Timeline

### [2026-09-11 10:00]
Session start; synced working-agent, LIS-transformer (ff 18 commits), LIS-transformer-v2 (switched feature branch → main). Transcribed recordings (first whole-file pass hallucinated after ~5 min; chunked re-run OK). Ran jest/tsc baselines in both repos. Read-only AKS inventory of 4 ConfigMaps + deployments. Wrote PLAN.md v0.1 with Phases 0–5, principles, risk table, draft ticket list, open questions. No code, no comments.
