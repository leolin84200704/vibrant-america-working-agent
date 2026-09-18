# Retiring /proxy and cloud-local-proxy — Classification and Migration Targets

**Epic:** VP-18260 · **Parent:** Trans v1 / v2 Optimization — Phased Plan · **Status:** classification rule agreed; three assignments pending caller identification

The agreed end state is that every `/proxy/*` route in trans v1 and the whole of `cloud-local-proxy` disappear. They are a 2023 artefact from when Azure and the on-prem network had no DNS between them; that gap closed years ago, and nothing should be reaching a destination through a wrapper any more.

This page turns that goal into per-endpoint assignments: for each route that is still in use, where it should live instead, who has to move, and what is blocking it. Retiring an endpoint nobody calls is bookkeeping. The work is the ones that are still in use, and the point of classifying them is that we are not obliged to leave them where they are — each one gets a better home and its downstream owner gets asked to migrate.

One distinction runs through the whole page and is worth stating up front, because it decides several of the assignments:

> **What gets deleted is the duplicated forwarding layer, not the authenticated edge.** `/proxy/*` and `cloud-local-proxy` are wrappers and they all go. `/trans/*` in trans v1 and the GraphQL / REST surface of trans v2 are not wrappers — they are the product's API. For PHI that edge is mandatory rather than optional, because the destinations behind it are either gRPC-only (core) or unauthenticated (the on-prem report server). "Call the destination directly" is correct for a service inside the cluster. It is not available to an end user.

---

## 1. What is actually running

Counted from trans v1 request logs — every request is logged, unlike APM spans which are sampled at roughly 0.4% and understate sparse traffic by two orders of magnitude. Window: the full 15 days Datadog retains, 2026-09-03 → 2026-09-18. The `TRANS_PROXY_GRPC_MODE` cutover that moved trans v2 onto direct gRPC landed 2026-09-16 22:03 UTC.

### `/proxy/grpc/*` — 6 routes

| Route | Before the cutover | 09-17 | 09-18 | State |
|---|---|---|---|---|
| `getTestStatus` | 120–1,876/day, in lockstep with `getQuestionaireBySampleId` every single day | 0 | 0 | Dead |
| `getQuestionaireBySampleId` | the same series, never differing by more than 1 | 0 | 0 | Dead |
| `listTnpCode` | 0, every day, including before the cutover | 0 | 0 | Dead |
| `getKitStatus` | ≈2× the first two (239–3,700/day) | 15 | 5 | **In use** |
| `getPatientTestsResult` | 1–5/day, flat, unaffected by the cutover | 5 | 3 | **In use** |
| `sendSkinPlacePatientOrders` | 0 (its known caller uses the on-prem proxy instead) | 0 | 0 | In use elsewhere |

The lockstep is what makes the first two safe to retire, rather than the zero days on their own: two routes tracking each other to within one call across 15 days, with a third at exactly twice the rate, is one caller's fixed per-sample pattern — trans v2's patientProfile — not a population of callers. A second, independent consumer would break the lockstep on the days it ran. It never breaks, and then both went to zero the day after that caller moved.

`getPatientTestsResult` is a different case and worth being precise about: its rate is flat straight through the cutover, so it was never on the migrated path. Whoever calls it has been calling it for at least 15 days.

### `/proxy/old-report/*` — 11 routes

| Route | 15-day traffic | State |
|---|---|---|
| `downloadTestOrderPDF` | **20,715** (≈1,380/day) | **In use — the busiest endpoint in the entire proxy family** |
| the other 10 | 0 | Dead |

All 11 are duplicates: trans v1's `trans-reports.controller.ts` serves the same 11 operations under `/trans/*`, calling the same `OldReportProxyService` class in-process. So deleting the `/proxy/old-report` copies removes a duplicated surface, not a capability — and removes the second of two implementations of the same PHI ownership gate, which is one fewer place for it to drift.

For comparison, over the same 15 days on the `/trans/*` twins: `GenerateBatchReqOrReportV2` 1,830, `downloadTestOrderPDF` 1,436, `GenerateOnlineZipDownloadV2` 8, `getOrderSummaryReportZip` 8, and the remaining 7 at zero. Of the 22 endpoints across both controllers, 5 carry traffic.

Note the ratio on `downloadTestOrderPDF`: the proxy copy takes **14× more traffic than the properly-gated one**. It is the dominant path for that operation, and we do not yet know who is using it.

### `cloud-local-proxy` — 18 routes

All 18 already have equivalents in trans v1. Callers are not enumerable from here: the cloud ingress and the on-prem ingress access logs are needed, and the on-prem side is not reachable from this team. One caller is known — `LIS-backend-billing` has `.../cloud-proxy/grpc/sendSkinPlacePatientOrders` hard-coded at `ProZOrderServiceImpl.java:115`.

Its `/old-report/*` copies do **not** carry the ownership gate that trans v1's versions gained under VP-17284. That makes it the weakest link in the compliance story and the strongest argument for retiring it first.

---

## 2. The classification rule

Two questions decide where an endpoint belongs. Neither is a matter of taste.

| Who calls it | What the wrapper actually adds | Where it belongs |
|---|---|---|
| A service inside the cluster | gRPC metadata, response normalisation | **The gRPC service, called directly.** The migrating service brings the metadata construction and the normalisation with it |
| A front end or an external consumer | gRPC metadata, response normalisation | **trans v2.** It already has the client, the metadata builder and an external GraphQL surface |
| A front end or an external consumer | A PHI ownership gate | **trans v1 `/trans/*`.** The gate is implemented there today and the operations already exist |

The middle row matters and is easy to skip past. Trans v2 already exposes `getKitStatus` as a GraphQL `@ResolveField` on the PNS resolver, and `patientProfile` already consumes kit data. If a still-unidentified caller of `/proxy/grpc/getKitStatus` turns out to be a front end, its migration target exists today and needs no new implementation.

---

## 3. Assignments

| Endpoint | Target home | Who migrates | Blocked on |
|---|---|---|---|
| `/proxy/grpc/getTestStatus` | — delete | nobody | announced, **VP-18320**, removal 2026-10-02 |
| `/proxy/grpc/getQuestionaireBySampleId` | — delete | nobody | as above |
| `/proxy/grpc/listTnpCode` | — delete | nobody | as above |
| `/proxy/grpc/getKitStatus` | in-cluster service → shipping gRPC `getKitStatusBySampleId`; front end → **trans v2 GraphQL** (exists today) | the calling team, once named | caller identity — LIS-transformer PR #800 |
| `/proxy/grpc/getPatientTestsResult` | in-cluster service → test-connect gRPC; front end → trans v2 | the calling team, once named | caller identity — PR #800 |
| `/proxy/grpc/sendSkinPlacePatientOrders` | `crmapi` directly — **only if the caller replicates the payload rewrite below**; otherwise it keeps exactly one wrapper | `LIS-backend-billing` | a ticket on the billing team |
| `/proxy/old-report/downloadTestOrderPDF` | **trans v1 `/trans/downloadTestOrderPDF`** — same operation, same service class, gate already present, already serving 1,436 calls | the calling team, once named | caller identity — needs the same attribution logging, which PR #800 does not cover |
| `/proxy/old-report/*` (other 10) | — delete | nobody | none; can join VP-18320 or take its own ticket |
| `cloud-local-proxy` (18 routes) | trans v1 equivalents, then each follows its row above | each caller | cloud + on-prem ingress access logs (on-prem needs Ray) |

---

## 4. What the wrappers actually add

Anyone migrating off a proxy route needs this list. None of these routes is pure forwarding, and each item below exists because something broke without it.

1. **JWT → gRPC metadata.** `createMetadataForCoresampleV2` propagates the caller's JWT subject to core. It is *not* an ownership check — the `/proxy/grpc` family has no ownership check at all, only authentication.
2. **A proto3 normalisation on kit lookups.** proto3 omits empty repeated fields on the wire, so a PO with no shipped packages arrives with `packages === undefined` and consumers crash reading `.length`. The wrapper fills it with an empty array. Leaving this out is Sentry #68038.
3. **A payload rewrite on `sendSkinPlacePatientOrders`.** The wrapper sets `comments` from `julien_barcode` before posting, and forwards the caller's `Authorization` header. A caller that goes straight to `crmapi` without replicating this will fail quietly rather than loudly.
4. **A cross-tenant PHI ownership gate on `/proxy/old-report/*`.** Customer and clinic are pinned from the authenticated JWT and never from the query or body; every requested sample must belong to the caller's clinic; navigators denied at customer level are rejected; trusted internal callers are cross-clinic by design and bypass it. Reading identity from `req.user` directly rather than through `resolveIdsForHttpOptional` is deliberate — the latter falls back to request arguments, which let an external caller spoof `internal_user_id` via a query parameter and skip the check entirely.

Trans v2's direct-gRPC path is the worked example that all of this is portable: PR #629 carried both the metadata construction and the proto3 normalisation across line by line, and the shadow comparison that followed agreed with the old path on 3,470 of 3,473 real requests. It worked because someone compared it line by line, not because the layer is thin.

---

## 5. What cannot move, and why

**The report family should not be rebuilt in trans v2.** Nineteen routes, a cross-tenant ownership gate, deep-link token resolution and PDF streaming, for zero latency benefit — the p95 on this family is spent in `lis-order` and `pdf-engine`, not in trans. Trans v2 has no report code at all today: its ConfigMap holds report keys, but nothing reads them. Re-implementing a compliance gate is precisely where the spoofing bypass above came from. If there is an independent decision to make trans v2 the single external edge, that is a project with its own justification and its own review; it should not ride along with proxy retirement.

**End users cannot be pointed at the report destination.** The destination behind `/proxy/old-report/*` is `192.168.x.x:8081/secure/nologin/...` — unauthenticated by construction. Sending customers there directly would remove the cross-tenant gate rather than relocate it. The gate would have to move into that server first, and that server is the thing being retired.

**Nothing can be assigned to an owner we cannot name.** Three of the five live endpoints are blocked on the same missing fact: who is calling them. At roughly half a call an hour, `/proxy/grpc` traffic is never sampled into a trace, so APM cannot answer it; and while `/proxy/old-report/downloadTestOrderPDF` is busy enough to sample, the header fields that identify a caller are not logged today.

---

## 6. Sequence

1. **Now.** Merge LIS-transformer PR #800 (logs `user-agent`, `x-forwarded-for` and the JWT subject on `/proxy/grpc/*`; log-only, tested). Open the equivalent for `/proxy/old-report/*` — the busiest endpoint in the family sits there and PR #800 does not cover it.
2. **2026-10-02.** VP-18320 removes the three dead `/proxy/grpc` routes after its announced two-week notice. The 10 dead `/proxy/old-report` routes can join it.
3. **~1 week after the logging lands.** Fill in the three pending assignments. The rule in §2 is already fixed; only the caller names are missing.
4. **Then.** One migration ticket per downstream owner, naming the target endpoint and a date, in the same shape as VP-18320.
5. **Last.** Delete the routes, then retire `cloud-local-proxy` once its caller list is complete and the 30-day zero-traffic clock has run.

---

## 7. Asks

- **Ray** — cloud and on-prem ingress access logs for `api.vibrant-america.com/v1/lis/cloud-proxy` and `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy`. This is the only thing that can enumerate `cloud-local-proxy`'s callers, and nothing downstream of it can start without that list.
- **Billing** — a ticket to move `sendSkinPlacePatientOrders` off the proxy, carrying the payload rewrite in §4.3.
- **Anyone calling a `/proxy/*` route** — say so on VP-18320. Our log retention is 15 days, so a job that runs monthly is invisible to us; a reply is the only way we find out before it breaks.
- **Repo admins** — mark the `typecheck + unit tests` job as a required status check on `main` in both trans repos. Until then a red PR check is advisory, and a merge to `main` is a deploy.
