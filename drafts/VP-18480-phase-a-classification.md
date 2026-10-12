# VP-18480 — LIS-Sample → trans, Phase A: caller inventory, route classification, migration runbook

> Draft for Leo's review before it goes onto the roadmap page (Confluence 2711453698 §5.3).
> Evidence: LIS-Sample `caller_attribution` request log (PR #187/#188, prod image `0a93d8bd`), Datadog
> `service:lis-sample-deployment @event:caller_attribution`, 2026-09-29T23:24Z → 2026-10-12T18:00Z (12.8 days),
> plus the cluster ConfigMap scan of 2026-09-29 and the org code search of the ticket.
> Leo's decision 2026-10-12: do not wait for day 14; routes at zero for the whole window are dead and get removed now.

## 1. Evidence window and method

| Item | Value |
|---|---|
| Window | 2026-09-29T23:24Z (first prod pod on the attribution image) → 2026-10-12T18:00Z |
| Source | One `caller_attribution` line per request from `LoggerMiddleware` on every route except `GET /healthcheck` (excluded by `LoggerModule.forRoot`); fields: method, route (Express pattern), status, user_agent, x-forwarded-for, remote_ip, auth (none / bearer), allow-listed JWT claims (internal_user_name, client_id, user_id, role) |
| Total requests | ≈ 338,000 across 66 route+method pairs; 3 prod pods; no staging data (staging pod had no traffic) |
| `ingress` vs `direct` | `x-forwarded-for` present = came through the public ingress `api.vibrant-wellness.com/v1/lis/samples/*` (Cloudflare → nginx); absent = in-cluster call straight to `lis-sample-service` (today only trans v2 and a few trans v1 calls do this) |
| Caller classes | **browser** = `Mozilla/*` UA with a user JWT (role internal / customer / patient); **service** = non-browser UA with a service identity (`internal_user_name` of a service or a token without user claims); **script** = non-browser UA carrying an individual's token |
| Limit of "zero" | 12.8 days covers every weekday twice and two weekends; it does NOT cover month-end or quarter-end jobs. No LIS-Sample route is wired to a cron or queue consumer (the three `@Cron` jobs are in the storage outbox drainer / storage import and do not call HTTP routes), and the zero-traffic routes below are all UI-triggered admin actions, so the month-end risk is bounded to "a human has not clicked it in 13 days" |

What code search alone could not see and the log did: `lis.results` (results family) uses only `POST /storage/records/samples/retrieval`; LIS-Shipping is the second-largest caller of `GET /patients/orders/operation-settings`; trans v2 calls `/patients/v2/kits` and `/status` in-cluster with a service token that carries no user claims; two individuals' tokens drive scripted traffic (python-requests / node / httpx / curl); 309 calls to `GET /patients/profiles` arrive with no token at all.

## 2. Caller table per route family

Counts are requests in the window. "74 staff" = distinct `internal_user_name` values seen on browser calls with role internal (LIS-frontend users). Routes at zero are in §7.

### 2.1 The LIS-frontend "sample page" bundle (≈16.8k each, 73–74 staff)

Ten routes are called together per sample-page view (same count, same user set). They are one aggregation candidate, not ten endpoints.

| Route | Calls | Browser staff | Non-browser callers | 4xx/5xx |
|---|---|---|---|---|
| `GET /order` | 16,826 | 74 | — | 170 |
| `GET /order/details` | 16,806 | 73 | — | 168 |
| `GET /order/check` | 17,170 | 74 | — | 171 |
| `GET /order/sample-level-info` | 16,763 | 73 | 4 direct, no claims (bearer) | 170 |
| `GET /patients/kits` | 16,753 | 73 | — | 168 |
| `GET /patients/profiles` | 17,135 | 74 | **309 `axios`, no token (`auth=none`), via ingress** | 168 |
| `GET /patients/orders/operation-settings` | 31,245 | 74 (16,899) | **Shipping Service 14,338** (`axios/1.15.2`, role INTERNAL) | 170 |
| `GET /tests` | 18,341 | 74 (16,823) | zichenzheng scripts 1,490 (node 1,462 / axios 26 / python 2); Shipping Service 27 | 180 |
| `GET /tubes/history` | 16,805 | 73 | — | 170 |
| `GET /status` | 26,185 | 74 (16,646) | **trans v2 service token 9,503 direct**; Trans v1 14; 14 no token; curl 1 | 24 |

The ≈170 errors per route are the same requests failing across the bundle (one bad sample id → ten 4xx), not ten independent problems.

### 2.2 Patients (remaining routes)

| Route | Calls | Callers | 4xx/5xx |
|---|---|---|---|
| `GET /patients/v2/kits` | 34,585 | **trans v2 service token 31,977** (22,858 direct + 9,119 ingress); **trans v1 forwarding the staff user's token ≈ 2,400** (`axios` + a staff `internal_user_name`, 47 distinct users, ingress+direct); `Jersey` (Java client) with a staff account 174; Trans v1 service identity 14; 14 no token | 38 |
| `PATCH /patients/profiles` | 271 | 17 staff | 0 |
| `GET /patients/resend-tubes` (not in OpenAPI) | 262 | 13 staff | 19 |
| `POST /patients/kits/resend` | 240 | 13 staff | 23 |
| `POST /patients/duplicate-check` | 119 | 13 staff; 7 patient-role browser; Data team (httpx) 1 | 1 |
| `GET /patients/pns-jwt` | 843 | 27 staff; Shipping Service 11 | 0 |
| `GET /patients/portal-jwt` | 493 | 23 staff; one engineer via curl 46 | 2 |
| `POST /patients/orders/batch/notif-email` | 136 | 5 staff; 1 customer-role browser | 0 |
| `POST /patients/orders/notif-email` | 100 | 13 staff | 0 |
| `POST /patients/orders/shipping-address/confirmation-email` | 16 | 1 staff | 0 |
| `POST /patients/orders/ny-waiver-form` | 11 | 5 staff | 0 |
| `POST /patients/orders/hormone-zoomer-qnr` | 4 | 3 staff | 0 |
| `POST /patients/orders/gut-zoomer-qnr` | 2 | 2 staff | 0 |

### 2.3 Order (remaining routes)

| Route | Calls | Callers | 4xx/5xx |
|---|---|---|---|
| `POST /order/check` | 6,330 | 9 staff | 93 |
| `GET /order/overviews` | 3,095 | 44 staff; zichenzheng scripts 20; 7 customer-role browser | 9 |
| `POST /order/attribute-value-check/batch` | 213 | 25 staff; 1 customer-role browser | 0 |
| `GET /order/patient-emails` | 207 | 12 staff | 1 |
| `POST /order/sample/validation` | 157 | 2 staff | 0 |
| `GET /order/audit-logs` | 100 | 23 staff; Data team (httpx) 4 | 0 |
| `PATCH /order/sample-level-info` | 86 | 13 staff; 4 direct, no claims | 1 |
| `POST /order/attribute-value-check` | 59 | 7 staff | 0 |
| `GET /order/clients` | 49 | 12 staff | 0 |
| `GET /order/clinics` | 39 | 10 staff | 0 |
| `POST /order/overviews/export` | 3 | 3 staff | 0 |

### 2.4 Storage

| Route | Calls | Callers | 4xx/5xx |
|---|---|---|---|
| `GET /storage/records` | 4,188 | **labsiteAPI / scripts under one individual's token: python-requests 3,175 + node 60**; 16 staff 951; 2 calls with no token | 10 |
| `POST /storage/racks/samples/tubes` | 3,286 | 6 staff | 1 |
| `POST /storage/records/samples/retrieval` | 2,171 | **lis.results 2,170** (results family, `axios`) | 0 |
| `GET /storage/racks` | 1,214 | 5 staff | 1 |
| `GET /storage/racks/dimension-list` | 910 | 22 staff | 30 |
| `GET /storage/racks/type-list` | 910 | 22 staff | 30 |
| `GET /storage/racks/:rack/samples/tubes` | 865 | 6 staff | 0 |
| `POST /storage/racks` | 380 | 6 staff | 4 |
| `DELETE /storage/racks/:rack` | 298 | 4 staff | 0 |
| `GET /storage/racks/suggestions` | 162 | 6 staff | 0 |
| `PUT /storage/racks/:rack` | 1 | 1 staff | 0 |

### 2.5 Record Management (all PermissionGuard, all browser staff)

| Route | Calls | Staff |
|---|---|---|
| `GET /record-management/providers/search` | 26 | 5 |
| `GET /record-management/providers/:customer_id/clinics` | 15 | 5 |
| `GET /record-management/providers/:customer_id/patients` | 11 | 3 |
| `GET /record-management/patients/search` | 10 | 3 |
| `GET /record-management/patients/:patient_id/order-total` | 8 | 3 |
| `GET /record-management/providers/:customer_id/samples` | 8 | 3 |
| `GET /record-management/practices/search` | 6 | 3 |
| `GET /record-management/clinics/:clinic_id` | 4 | 2 |
| `POST /record-management/merge-patients` | 3 | 3 |
| `POST /record-management/transfer-provider-practice` | 2 (1 err) | 1 |
| `POST /record-management/transfer-selected-patients` | 2 | 2 |
| `POST /record-management/transfer-selected-orders` | 1 | 1 |

### 2.6 Small families

| Route | Calls | Callers | 4xx/5xx |
|---|---|---|---|
| `GET /coupon` | 830 | 27 staff | 0 |
| `GET /interaction-logs` | 154 | 4 staff | 0 |
| `POST /interaction-logs` | 124 | 2 staff | 0 |
| `GET /phlebotomists` | 76 | 2 staff (route has no guard) | 0 |
| `POST /tests/rerun` | 39 | 4 staff | 0 |
| `PATCH /tubes/info` | 10 | 6 staff | 9 |
| `POST /tests/tnp/partial-spun` | 2 | 1 staff | 2 |
| `GET /` | 1 | one browser, no token | 0 |
| `GET /*` (not a route; 404 probe) | 1 | python-httpx, no token | 1 |

### 2.7 Consumers (who must move), from log + ConfigMap scan + code search

| Consumer | Evidence | Routes used | Traffic |
|---|---|---|---|
| LIS-frontend (`samplePageRequest.js`, `SampleLogService.js`) | browser, role internal, 74 staff | everything in §2.1–2.6 except service rows | ≈ 290k |
| LIS-Shipping (`lis-shipping-config-prod` `LIS_SAMPLE_HTTP_URL`, public URL) | `axios/1.15.2`, `internal_user_name = Shipping Service` | `GET /patients/orders/operation-settings`, `GET /patients/pns-jwt`, `GET /tests` | 14,376 |
| trans v2 (`lis-transv2-config` `get_pns_kit_status`, `get_pns_sample_status`, `sample_url`, in-cluster) | `axios/1.16.0`, bearer with no user claims, mostly `direct` | `GET /patients/v2/kits`, `GET /status` | 41,480 |
| trans v1 (`lis-trans-config` `getKitStatusV2`, `sample_url`; moved in-cluster by VP-18460 batch 4) | `axios` with the end user's token forwarded, plus service identity `Trans v1` | `GET /patients/v2/kits`, `GET /status` | ≈ 2,450 |
| results family (`SAMPLE_STORAGE_BASE_URL` in results-core / results-grpc / results-web ConfigMaps, public URL; staging mirrors point at PROD) | `axios`, `internal_user_name = lis.results` | `POST /storage/records/samples/retrieval` | 2,170 |
| labsiteAPI (`app/api/sales.py`) + a node script | `python-requests/2.31.0` and `node`, **both carrying one individual's token (zichenzheng)** | `GET /storage/records`, `GET /tests`, `GET /order/overviews` | ≈ 4,740 |
| Data team | `python-httpx/0.28.1`, `internal_user_name = Data team` | `GET /order/audit-logs`, `POST /patients/duplicate-check` | 5 |
| One engineer via curl | `curl`, personal token | `GET /patients/portal-jwt` | 46 |
| Unknown Java client | `Jersey` UA with a staff account's token | `GET /patients/v2/kits` | 174 |
| Unknown unauthenticated caller | `axios`, `auth=none`, via ingress | `GET /patients/profiles` 309; `/patients/v2/kits` 14; `/status` 14 | 337 |
| vibrant-wellness-portal (`UserConfig.js`), pns-portal (`requests.js`), PNS-Singlepage | browser rows with role customer (9) and patient (7) | `GET /order/overviews`, `POST /patients/duplicate-check`, `POST /order/attribute-value-check/batch`, `POST /patients/orders/batch/notif-email` | 16 — these portals barely use LIS-Sample from the browser; which of the three sent which row cannot be told from the log |
| LIS-backend-v2-order-management (Go, `service/foreign/sample_service.go`) | code search only; no `Go-http-client` UA in the window | — | **0 — dormant or dead integration; confirm with the order-management owner before deleting the client** |
| lis-accounting (`lis-accounting-config` `LIS_SAMPLE_SERVICE_BASE`, in-cluster svc) | ConfigMap only; no accounting identity and no unexplained `direct` traffic besides trans | — | **0 — dormant; the only `direct` no-claims rows match trans v2's token** |

## 3. Classification per route

Rule: **PHI-gated** = returns or mutates patient-identifiable data and must keep an ownership gate (JwtAuthGuard + customer/clinic/patient scoping) when it moves; **aggregation** = composes several Core/shipping/results calls for one UI view and is only called by LIS-frontend; **service-to-service** = ≥ 95 % of calls come from a service identity, so the right shape in trans is an RPC (or an in-process call once the caller is trans itself); **dead** = zero calls in the window. A route can be PHI-gated and aggregation at once; the first column is what decides the gate, the second what decides the shape.

| Family | Route(s) | Class | Notes |
|---|---|---|---|
| Sample-page bundle | the ten routes in §2.1 | PHI-gated + aggregation | 73–74 staff, one page. `GET /patients/profiles` has **no guard in code** (`patients.controller.ts:112`) and receives 309 token-less calls — gate must be added when it moves, after the unknown caller is identified |
| Patients | `GET /patients/v2/kits` | **service-to-service** (99 %) + PHI-gated | trans v2 31,977 + trans v1 ≈ 2,450 of 34,585. The Phase C family (VP-18482) |
| Patients | `GET /patients/pns-jwt`, `GET /patients/portal-jwt` | PHI-gated (token minting for a patient / portal session) | pns-jwt has no guard in code; portal-jwt is PermissionGuard |
| Patients | `PATCH /patients/profiles`, `/kits/resend`, `/resend-tubes`, `/duplicate-check`, notif-email ×2, confirmation-email, ny-waiver-form, zoomer-qnr ×2 | PHI-gated | staff-only mutations and emails; low volume |
| Order | `POST /order/check`, `/order/overviews`(+export), `/patient-emails`, `/sample/validation`, `/audit-logs`, `/attribute-value-check`(+batch), `PATCH /sample-level-info`, `/clients`, `/clinics` | PHI-gated | staff; `/order/overviews` and `/audit-logs` also scripted (Data team, zichenzheng) |
| Storage | racks ×9, `GET /storage/records` | PHI-gated (records carry sample ids) — **data-plane bound** | the only family with its own tables: `lis_inventory` (master) + `vibrant_america_information` (master/slave) + Redis + Service Bus outbox drainer (`@Cron */10s`, daily 03:00) + storage import cron (daily 09:15). Cannot move before Phase B |
| Storage | `POST /storage/records/samples/retrieval` | **service-to-service** (100 % lis.results) | one RPC for the results family |
| Record Management | 12 live routes | PHI-gated (admin transfers / merges) | PermissionGuard everywhere; pure Core gRPC composition (customer/patient services), no DB |
| Tests | `GET /tests` (bundle), `POST /tests/rerun`, `/tnp/partial-spun` | PHI-gated | `/tests` also Shipping Service 27 + scripts 1,490; uses Core gRPC + trans v1 `TransService` gRPC + results-grpc |
| Tubes | `GET /tubes/history` (bundle), `PATCH /tubes/info` | PHI-gated | shipping gRPC + `lis_inventory` |
| Status | `GET /status` | PHI-gated + **service-to-service for 36 %** (trans v2 9,503 direct) | composes Core sample gRPC + trans v1 gRPC + HTTP to trans/shipping/order; the trans v2 → LIS-Sample → trans v1 loop is the same three-hop shape as `getKitStatusV2` |
| Coupon | `GET /coupon` | aggregation (accounting coupon usage via an admin JWT minted in `utils`) | staff only |
| Interaction Logs | `GET`, `POST /interaction-logs` | PHI-gated (ticket text about samples) | `lis_inventory` + `vibrant_tracking` (slave) + Core gRPC |
| Phlebotomists | `GET /phlebotomists` | aggregation (Core sample gRPC fuzzy search) | **no guard in code**; 76 staff calls |
| Notifications | 4 routes | **dead** | pure pass-through to Core `NotificationService` gRPC |
| Customers | `GET /customers` | **dead** | shipping gRPC search; no guard in code |
| Patients / Order / Storage / Record Mgmt / Interaction Logs | the 18 routes in §7 | **dead** | |

## 4. Target home per family

Trans v1 (`LIS-transformer`) is the REST aggregator for LIS-frontend staff screens and already exposes the `TransService` gRPC that LIS-Shipping, LIS-Sample and results-grpc consume; trans v2 (`LIS-transformer-v2`) serves the patient/PNS side (GraphQL resolvers, `patientProfile`, `get_pns_kit_status`). Home follows the caller, and the shape follows the class.

| Family | Home | Shape | Why | Data plane needed |
|---|---|---|---|---|
| `GET /patients/v2/kits` | **trans v2 in-process** (Phase C, VP-18482), plus a trans v1 in-process port of the same function | function call | 92 % of calls are trans v2's own `get_pns_kit_status`; trans v1's `getKitStatusV2` three-hop (trans v1 → public ingress → LIS-Sample → trans v1 `/trans/patientTestKitInfo`) disappears when v1 calls the same function locally (VP-18469) | shipping gRPC + Core sample gRPC only (no LIS-Sample DB) |
| `GET /status` | trans v1 in-process; trans v2 calls it via `TransService` gRPC (new RPC `GetSampleStatus`) instead of HTTP | RPC for v2, function for v1 | the LIS-frontend 16.6k calls come through trans v1 anyway; today's v2 → LIS-Sample → v1 loop becomes v2 → v1 | Core gRPC, results-grpc, shipping |
| Sample-page bundle (Order ×4, Patients ×2, operation-settings, tests, tubes/history) | **trans v1 in-process**, exposed as ONE aggregate REST call for LIS-frontend plus the ten legacy paths kept until LIS-frontend switches | function | same 74 users, same page; trans v1 is where LIS-frontend aggregation lives; cuts ten round trips to one | Core gRPC, shipping gRPC, results-grpc, `lis_inventory` for tubes/tests (Phase B) |
| `GET /patients/orders/operation-settings` for LIS-Shipping | trans v1 `TransService` gRPC (new RPC) | RPC | 14,338 calls/13 d from a service; LIS-Shipping already holds a trans v1 gRPC client | same as above |
| `POST /storage/records/samples/retrieval` for results | trans v1 `TransService` gRPC (new RPC) | RPC | 100 % lis.results; results-grpc already holds a trans v1 gRPC client | `lis_inventory` + `va_info` (Phase B) |
| Storage racks/records (staff) | trans v1 in-process | function | staff-only; last family, after Phase B proves the outbox drainer and import cron run exactly once inside trans | all three DBs, Redis, Service Bus outbox + `storage-info-updates` consumer, both crons |
| Order (non-bundle), Patients mutations/emails, Tests, Tubes, Interaction Logs, Coupon, Phlebotomists, Record Management | trans v1 in-process | function | staff-only; Record Management is pure Core composition and is the cheapest family to port | Core gRPC (+ `lis_inventory`, `vibrant_tracking` for interaction logs) |
| `GET /patients/pns-jwt`, `GET /patients/portal-jwt` | trans v1 in-process | function | staff minting patient/portal sessions; Shipping's 11 pns-jwt calls move to the same RPC surface as operation-settings | JWT secrets only |
| Notifications, Customers, 18 dead routes | **none — delete** | — | zero traffic; Notifications is a 1:1 pass-through to Core `NotificationService` which LIS-frontend can call through trans v1's existing Core client if ever needed | — |

Open choice for Leo: whether the staff families go to **trans v1** (recommended above: that is where LIS-frontend aggregation and the staff gRPC surface already live, and it keeps trans v2 patient-only) or to **trans v2** (newer codebase, GraphQL, but no LIS-frontend REST surface today). The runbook below assumes trans v1.

## 5. Per-consumer runbook

Shape as the proxy runbook (VP-18324): each consumer changes one thing, in one place, with the previous value recorded; shadow before flip; flip is a ConfigMap value or an ingress rule, never a code deploy; 30 days at zero before deletion.

Order of operations (families in value order): **(0) dead routes now → (1) kits [Phase C] → (2) status → (3) service RPCs (operation-settings, storage retrieval) → (4) sample-page bundle → (5) staff families → (6) storage racks/records → (7) ingress rewrite + LIS-Sample scale-to-zero.**

| # | Consumer | Today | Change | To | When | Rollback |
|---|---|---|---|---|---|---|
| 1 | trans v2 (`lis-transv2-config`, `-st`) | `get_pns_kit_status` = `http://lis-sample-service.sample.svc.cluster.local/.../patients/v2/kits`; `get_pns_sample_status`, `sample_url` | replace the HTTP call with the in-process kit function (flag `TRANS_KITS_INPROCESS=shadow|on`, same pattern as `TRANS_PROXY_GRPC_MODE`); `get_pns_sample_status` → `TransService.GetSampleStatus` gRPC on trans v1 | no URL (function); `lis-trans-service.default.svc.cluster.local:3146` gRPC | after Phase C shadow diff = 0 for a week | flag back to `http` |
| 2 | trans v1 (`lis-trans-config`, `-st`) | `getKitStatusV2` → LIS-Sample `/patients/v2/kits` (three-hop); `sample_url` | call the in-process kit function (closes VP-18469); `sample_url` → local status function | — | with #1 | flag back |
| 3 | LIS-Shipping (`lis-shipping-config-prod`, `-staging`) | `LIS_SAMPLE_HTTP_URL` = public `api.vibrant-wellness.com/v1/lis/samples` (prod) / `.../samples/staging` | switch `operation-settings`, `pns-jwt`, `tests` calls to `TransService` RPCs (Shipping already has the trans v1 gRPC client) | `lis-trans-service...:3146` gRPC | after step 3 RPCs shadow-verified | keep `LIS_SAMPLE_HTTP_URL` until 30 days at zero |
| 4 | results-core / results-grpc / results-web (`results/*-config`, `lis-results-staging/*-mirror-config`) | `SAMPLE_STORAGE_BASE_URL` = public `api.vibrant-wellness.com/v1/lis/samples/` — staging mirrors point at **prod** | `POST /storage/records/samples/retrieval` → `TransService.RetrieveStorageRecords` RPC (results-grpc already has the client); fix the staging mirrors to the staging trans at the same time | gRPC | after Phase B (needs `lis_inventory` + `va_info` in trans) | ConfigMap value back |
| 5 | LIS-frontend | `samplePageRequest.js` calls ten `/v1/lis/samples/*` routes per sample page; `SampleLogService.js` interaction logs | point the base URL at trans v1's `/v1/lis/trans-service/samples/*` (same paths, served by trans) once the ingress rule exists; then adopt the single aggregate call | ingress path on trans | step 4 → 5 | base URL back |
| 6 | labsiteAPI (`app/api/sales.py`) + node script | `GET /storage/records`, `/tests`, `/order/overviews` with an individual's token | replace the personal token with a service client (OAuth2 client_credentials, `internal_user_name` of the service); then follow the ingress rewrite | — | before step 7 (also a security fix independent of the merge) | — |
| 7 | Data team (httpx), curl user | personal tokens | same as #6 | — | before step 7 | — |
| 8 | vibrant-wellness-portal, pns-portal, PNS-Singlepage | ≤ 16 browser calls in 13 d | follow the ingress rewrite; nothing else | — | step 7 | — |
| 9 | LIS-backend-v2-order-management (Go), lis-accounting | configured, zero traffic | confirm with owners, delete the client / ConfigMap key | — | before step 7 | — |
| 10 | Ingress `/v1/lis/samples/*` → `lis-sample-service` | one rule | per family, add a more specific path rule pointing at `lis-trans-service` (e.g. `/v1/lis/samples/patients/v2/kits` first), shadow via record/replay (VP-18459), flip, 30 days; at the end a permanent rewrite `/v1/lis/samples/(.*)` → trans `/samples/$1` so external URLs keep working, then scale LIS-Sample to zero | trans | last | remove the specific rule |

## 6. Sizing per family and dependencies

| Family (ticket) | SP | Depends on | Notes |
|---|---|---|---|
| Dead routes removal (this ticket, PR now) | 3 | — | 18 routes + Notifications/Customers modules + their DTOs/specs |
| Kits `/patients/v2/kits` | in VP-18482 (32) | Phase 0 harness VP-18459; Phase B not required (no LIS-Sample DB) | also closes VP-18469 |
| Status `/status` | 8 | kits | new `TransService.GetSampleStatus` RPC for trans v2 |
| Service RPCs: operation-settings (Shipping), storage retrieval (results) | 10 | Phase B for storage retrieval only | two RPCs + two client PRs (LIS-Shipping, results-grpc) |
| Sample-page bundle (Order ×4, Patients ×2, tests, tubes/history, operation-settings, status) | 24 | Phase B (`lis_inventory` for tubes/tests) | one aggregate endpoint + ten legacy paths; LIS-frontend PR |
| Patients remainder (mutations, emails, jwt minting) | 10 | — | add the missing guard on `/profiles` and `/pns-jwt` on the way |
| Order remainder | 10 | — | |
| Record Management | 6 | — | pure Core composition |
| Tests + Tubes + Interaction Logs + Coupon + Phlebotomists | 10 | Phase B (`lis_inventory`, `vibrant_tracking`) | add the missing guard on `/phlebotomists` |
| Storage racks/records (staff) | 20 | **Phase B (VP-18481)** fully: 6 Prisma clients, Redis namespaces, outbox drainer + `storage-info-updates` consumer exactly-once, import cron | last family |
| Ingress rewrite + LIS-Sample scale-to-zero + repo archive | 5 | all above, 30 days at zero | |

Phase B (VP-18481) is on the critical path for storage retrieval, the bundle (tubes/tests tables) and the storage family; kits, status, record management and the pure-Core families can start as soon as Phase C's harness exists.

## 7. Dead routes — remove now (Leo, 2026-10-12)

18 OpenAPI operations with zero calls in the window (`/healthcheck` is excluded from the log, not dead). Removal PR: `feature/leo/VP-18480-remove-dead-routes` on LIS-Sample (`dev` → staging, `master` → prod, one PR per base as the repo convention), controller methods + services + DTOs + specs + the OpenAPI entries; whole `notifications` and `customers` modules go.

| Route | Module | What it wrapped |
|---|---|---|
| `GET /notifications/active`, `POST /notifications`, `PATCH /notifications/:id`, `DELETE /notifications/:id` | notifications | Core `NotificationService` gRPC pass-through |
| `GET /customers` | customers | shipping gRPC customer search (no guard) |
| `GET /patients` | patients | patient list |
| `POST /patients/complete-reports` | patients | PermissionGuard |
| `POST /patients/orders/cardio-zoomer-qnr`, `/hormone-qnr`, `/nutriproz-skincare-qnr`, `/disclosure-restricted-notif` | patients | questionnaire / notice emails |
| `GET /interaction-logs/:id/details`, `POST /interaction-logs/resolution` | interaction-logs | |
| `POST /record-management/transfer-all-orders`, `/transfer-all-patients` | record-management | PermissionGuard bulk transfers |
| `POST /storage/records/batch/removal` | storage | |
| `PUT /storage/racks/samples/tubes/:idx`, `DELETE /storage/racks/samples/tubes/:idx` | storage | |

Also in the controller but in neither OpenAPI nor the log: `POST /patients/orders/reset-questionnaire` (`patients.controller.ts:363`) — remove with the rest. Undocumented but live: `GET /patients/resend-tubes` (262 calls) — add to OpenAPI, keep.

## 8. Open items

1. **309 token-less `GET /patients/profiles`** (plus 14 on `/patients/v2/kits`, 14 on `/status`): `axios/1.19.0`, via the public ingress, `auth=none`, queried by `accession_id`, HTTP 200. Resolved 2026-10-12 from the pod log: `cf-connecting-ip` = `45.24.217.146` on every sampled call — the same egress IP the LIS-frontend staff sessions come from (their `origin` is `http://192.168.60.2:8002`). So it is a lab-network script or internal tool, not an outside party. Still unidentified by name; the route has no guard, so it succeeds. Find the host on the lab LAN (ask IT for the NAT log for 45.24.217.146 → axios 1.19.0) before adding the guard.
2. **`Jersey` Java client** on `/patients/v2/kits` (174 calls) using a staff account: not EMR-Backend (0/0 replicas). Candidate: a Java tool run by that account; ask the account owner.
3. **Personal tokens in scripts**: labsiteAPI + a node job (zichenzheng, ≈ 4,740 calls), Data team httpx (5), curl (46). These break when the token expires and bypass service attribution; move to service clients before the ingress rewrite.
4. **Unguarded routes in code**: `GET /patients/profiles`, `GET /patients/pns-jwt`, `GET /phlebotomists`, `GET /customers` (dead). Add guards when the family moves; `/profiles` first (PHI, token-less traffic observed).
5. **Log leak (pre-existing, separate ticket)**: `src/app.module.ts:73` pino `serializers.req` returns the whole request, so every log line in a request context carries `headers.authorization` (full JWT) and the request body (patient emails etc.) into Datadog — 16,220 such lines in six hours on prod. Not caused by the attribution middleware; fix is a redact list + body allow-list.
6. **Phase C's staging rehearsal**: results and shipping staging ConfigMaps point at the PROD LIS-Sample URL, so a staging shadow of the storage-retrieval RPC compares against prod data; fix the mirrors first (runbook #4).
7. Home decision trans v1 vs v2 for the staff families (§4) — Leo.
