# Jira comment drafts — Trans Opt wave 1 (2026-09-29). NOT posted. Leo reviews, then I post or he posts.

## VP-18485
Fix is smaller than the ticket assumed: `src/redis_s.ts` is dead code. Nothing imports it (only the jest setupFiles mock referenced it), so the client existed only to dial the on-prem Redis from every pod at boot — that is the `[ioredis] Unhandled error event: connect ETIMEDOUT` line seen once per pod on every trans v1 restart in AKS (3 on the 17:07Z restart, 3 on the 18:26Z one today).
PRs: LIS-transformer #843 (main) and #844 (stage_test), both draft. Delete the file + the mock; `src/redis.ts` and the calendar client already read `Azure_redis_pass` from env.
Rotation still required and NOT done: the same literal is in `LIS-setting-consumer/src/redis-sentinal.ts` (non-cloud, non-stprod branch). The instance is the on-prem `192.168.60.9:4646`; owner to confirm (Ray?). Note for whoever rotates: `LIS-accounting-wsgi` talks to the Sentinel on `:26390` without a password, so it is a different instance and unaffected.

## VP-18461
Done in all four ConfigMaps. Re-confirmed 0 code reads at current main of both repos (only hits: `LIS-transformer/docs/proxy-migration-configmap.md`, which already lists them as stale, and the committed ConfigMap copy `LIS-transformer-v2/config.yaml`, which is VP-18458's problem).
- `default/lis-trans-config-st` 166 -> 152 keys, `transv2/lis-transv2-config-st` 153 -> 145 (18:14Z), both -st deployments restarted and healthy.
- `transv2/lis-transv2-config` 157 -> 149 (18:20Z, rolled 3/3); `default/lis-trans-config` 163 -> 149 (18:25Z, rolled 3/3 together with VP-18460 batch 1).
- Deleted values are recorded in the STM (`storage/short_term_memory/VP-18461.md`); rollback = `kubectl patch` them back, no restart needed for the point of this ticket.
Smoke = the restarts themselves (nothing reads the keys, so the proof is that nothing changed): prod trans v1 error patterns during the 18:26–18:28Z rollout are identical to the 17:07–17:08Z rollout someone else did earlier (npm notices, the redis_s ETIMEDOUT, dd-trace stack lines).

## VP-18460
Batch 1 (base-report, 7 keys) done on staging 18:20Z and prod 18:25Z. Before switching, from inside the trans pod itself I fetched every one of the 7 URLs both ways (public ingress vs `lis-base-report.report.svc.cluster.local:30800`, same bearer token, real accession) and compared bytes: 7/7 identical on staging (incl. a 636 KB PDF) and 7/7 identical on prod (incl. an 821 KB PDF); unauthenticated both sides return 401, so the ingress injects nothing the service depends on (the ingress only has `rewrite-target` and `proxy-body-size`). Previous values recorded in the STM. Next batch (shipping, 4 keys) after 24 h of p95/error watch, i.e. not before 2026-09-30 18:30Z.

## VP-18462
Prod is on `shadow`, not yet `grpc`: added `SETTING_GRPC_MODE=shadow` + prod `SHIPPING_RPC` / `TEST_RESULT_RPC` (mirroring the trans v1 prod values, Services confirmed in `shipping` / `results`) to `lis-setting-consumer-config` and `-local-config` at 18:17Z, both deployments rolled 3/3. Shadow serves the proxy answer and logs `grpc_shadow` with any difference; at ~10 calls/day this needs about a day to accumulate. Flip to `grpc` after the first clean window. `#180` already removed the prod-address defaults, so unset URLs mean proxy, not prod. `-local-st` still has none of the three keys (untouched, decision pending).
Note: `kafka.consumer.crash` lines right after the restart are not new — Datadog shows them every day for the last 15 days (peaks 09-16, 09-21, 09-23, 09-28) independent of deploys.

## VP-18464
Cloud side done; on-prem still needs Ray. Findings:
1. Ingress access logs are not in Datadog: the agent DaemonSet's `DD_CONTAINER_EXCLUDE` drops `app-routing-system` and `ingress-basic`. No nginx metric series for the cloud-local ingress either.
2. Only 36 h of access log exists (controller pod restarted 09-28 06:12Z). In it: 0 requests to `/v1/lis/cloud-proxy*` on prod and -st (3 probe hits from me excluded).
3. The proxy pods log nothing per request except two routes. Datadog 15 d: one burst of ~101 `checkIfPersonalizedReportCanBeCreated` calls 09-14 18:15–18:29Z (70 sample ids), then 0. Not from lis-trans (inlined since 05-21). Caller identity unrecoverable (Cloudflare edge IPs only, no UA/JWT logged).
4. `LIS-backend-billing`'s hardcoded URL is `www.vibrant-america.com/lisapi/...` = the on-prem instance; it never reaches the AKS deployment.
To get a real 30-day zero window: un-exclude `app-routing-system` from the agent (or read Cloudflare per-path analytics). Recommendation, not done.
