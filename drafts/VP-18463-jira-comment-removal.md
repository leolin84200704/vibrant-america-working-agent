# VP-18463 — progress comment (DRAFT, not posted; post after #927 is deployed to prod)

Removal done one day ahead of the notice (decided 2026-10-13); the zero window was
already clean and nobody objected.

**Keys (2026-10-13 22:4xZ).** `proxy_getkit` / `proxy_getresult` removed from the four
setting-consumer ConfigMaps (`lis-setting-consumer-config`, `-local-config`, `-st-config`,
`-local-st-config`). Every setting-consumer pod was already running `SETTING_GRPC_MODE=grpc`,
so no restart was needed. No ConfigMap in the cluster references `/proxy/grpc` any more.

**Routes.** LIS-transformer #925 -> `stage_test` (deployed 23:00Z, 4c46d5e):
`/proxy/grpc/getKitStatus` and `/proxy/grpc/getPatientTestsResult` return 404, a live
`/trans/*` route still answers, no error-level log at boot. #927 -> `main` carries the
same change plus the API contract snapshot update; prod result will follow in this
thread once it is deployed.

Evidence for the zero window: Datadog per-request logs on every `/proxy/*` path,
2026-09-30 18:21Z to 2026-10-13 19:00Z, prod and staging = 0; `proxyGrpcCaller`
attribution events = 0 (positive control on `/trans/findPatient`: 1164 rows in 2 h).

The `/proxy` surface of trans v1 is now empty: `ProxyController`, its DTOs and the
caller-attribution interceptor are deleted; `ProxyModule` survives only as the provider
of `ProxyService` / `OldReportProxyService` / `OrderSummaryPdfService` for `/trans/*`.
