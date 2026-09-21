# Retiring /proxy and cloud-local-proxy — Classification and Migration Targets

**Epic:** VP-18260 · **Parent:** Trans v1 / v2 Optimization — Phased Plan · **Status:** every assignment resolved. The last unknown caller was identified on 2026-09-21 by attribution logging in production, and the one interim migration has a recipe measured on staging

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

## 3. Assignments — every endpoint has a destination

No route on this page is "stuck". Where a caller is still unidentified, that decides *which branch* a route takes, never *whether* it has a direction — the destination follows from the domain and the actual downstream, both of which are known today.

| Endpoint | What it really talks to | Destination | Who moves | Waiting on |
|---|---|---|---|---|
| `/proxy/grpc/getTestStatus` | test-connect gRPC | delete | nobody | **VP-18320**, removal 2026-10-02 |
| `/proxy/grpc/getQuestionaireBySampleId` | interactive-report gRPC | delete | nobody | as above |
| `/proxy/grpc/listTnpCode` | test-connect gRPC | delete | nobody | as above |
| `/proxy/grpc/getKitStatus` | shipping gRPC `getKitStatusBySampleId` | **LIS-setting-consumer** is the caller and it is an in-cluster service, so the branch is settled: the owning service's own API, as a **code change** in that repo — not a config swap. See the runbook | LIS-setting-consumer | scheduling |
| `/proxy/grpc/getPatientTestsResult` | test-connect gRPC | Same caller, same branch, also a **code change**. Its call sits behind a 500-second Redis cache whose key and shape must survive the move | LIS-setting-consumer | scheduling |
| `/proxy/grpc/sendSkinPlacePatientOrders` | `crmapi` over the public internet | **`crmapi` directly**, with the payload rewrite in §4.3 carried by the caller | `LIS-backend-billing` | a ticket on that team |
| `/proxy/old-report/downloadTestOrderPDF` | **lis-order, twice** (order summary + redraw), merged | **Interim:** `/trans/downloadTestOrderPDF` plus one added parameter — recipe measured, see §5. **Target:** lis-order | LIS-setting-consumer, then lis-order | scheduling; lis-order's roadmap |
| `/proxy/old-report/*` (other 10) | — | delete | nobody | none |
| `/trans/downloadTestOrderPDF` | same as above | **lis-order** — see §5 | lis-order | that team's roadmap |
| `/trans/GenerateBatchReqOrReportV2` | on-prem report server `192.168.60.77:8081/secure/nologin/…` | **base-report-service** — see §6 | report team | that team's roadmap |
| `/trans/GenerateOnlineZipDownloadV2` (8 calls / 15 days) | same on-prem server | base-report-service, or delete — the traffic barely justifies a migration | report team / front end | a usage decision |
| `/trans/getOrderSummaryReportZip` (8 calls / 15 days) | same on-prem server | as above | report team / front end | a usage decision |
| `/trans/*` report routes (other 7) | — | delete | nobody | front-end confirmation |
| `cloud-local-proxy` (18 routes) | trans v1 has an equivalent for all 18 | callers move to trans v1's `/trans/*` (which has the ownership gate its copies lack), then follow the rows above | each caller | cloud + on-prem ingress logs (Ray) |

---

## 4. What the wrappers add — bring this with you

None of these routes is pure forwarding. Every item below exists because something broke without it.

1. **JWT → gRPC metadata.** `createMetadataForCoresampleV2` propagates the caller's JWT subject to core. It is *not* an ownership check — the `/proxy/grpc` family has authentication only.
2. **A proto3 normalisation on kit lookups.** proto3 omits empty repeated fields, so a PO with no shipped packages arrives with `packages === undefined` and consumers crash on `.length`. The wrapper fills it with an empty array. Omitting this is Sentry #68038.
3. **A payload rewrite on `sendSkinPlacePatientOrders`.** The wrapper sets `comments` from `julien_barcode` before posting and forwards the caller's `Authorization`. Going straight to `crmapi` without replicating it fails quietly rather than loudly.
4. **A cross-tenant PHI ownership gate on `/proxy/old-report/*` and `/trans/*`.** Customer and clinic are pinned from the authenticated JWT and never from query or body; every requested sample must belong to the caller's clinic; navigators denied at customer level are rejected; trusted internal callers are cross-clinic by design and bypass it. Identity is read from `req.user` directly rather than through `resolveIdsForHttpOptional`, deliberately — the latter falls back to request arguments, which let an external caller spoof `internal_user_id` through a query parameter and skip the check entirely.

Trans v2's direct-gRPC path is the proof all of this is portable: PR #629 carried items 1 and 2 across line by line, and the shadow comparison that followed agreed with the old path on 3,470 of 3,473 real requests. It worked because someone compared it line by line, not because the layer is thin.

**A defect to fix wherever this endpoint ends up.** `downloadTestOrderPDF` writes its PDFs to the pod's working directory under a filename derived only from `sample_id` (`<sample_id>_downloadTestOrderPDF_newordersummary.pdf`). Two concurrent requests for the same sample therefore share filenames, and one request's `end` handler `unlinkSync`s a file the other may still be streaming. At ~1,380 requests a day this is a live race, not a theoretical one, and in the meantime PHI sits on the pod filesystem. This wants its own ticket regardless of which service owns the endpoint.

---

## 5. `downloadTestOrderPDF` belongs in lis-order, not in a report service

The name is misleading. Despite living under `old-report`, this endpoint has no relationship to `base-report-service`: both of its data sources are **lis-order** (`/v1/portal/order/…`), it produces an *order summary* document rather than a lab report, and `base-report-service` neither owns nor generates those PDFs. Moving it there would recreate a hop — report-service calling lis-order — which is the shape being deleted.

What the endpoint actually does is orchestration: fetch the order summary and the redraw order summary in parallel, branch on the four combinations of 200/204 against `order_status`, merge the two PDFs, stream the result, delete the temp files. Both inputs are lis-order's own documents, so lis-order can collapse the whole thing into a single call and the merge disappears as a cross-service concern.

Two steps, and the first does not wait for the second:

| | Now | Later |
|---|---|---|
| Action | point `LIS-setting-consumer` at `/trans/downloadTestOrderPDF` and add one query parameter | lis-order takes the endpoint |
| New code | one line in the caller — see the measured recipe below | a new endpoint on another team's service |
| Unlocks | deleting all 11 `/proxy/old-report` routes | two cross-service calls and a PDF merge collapse into one call; trans stops holding PDFs on disk |

**The caller is confirmed, not inferred.** Attribution logging went live on this route on 2026-09-21. Every request comes from the three `lis-setting-consumer` replicas — same pod addresses, same `axios/1.4.0`, same `user_id: 0` service token seen on the gRPC routes. Configuration evidence and traffic now agree.

**The migration recipe, measured rather than reasoned about.** A probe from inside the staging setting-consumer pod, using that pod's own OAuth2 service token, called both routes with the caller's exact query string:

| Request | Result |
|---|---|
| `/proxy/old-report/downloadTestOrderPDF`, as the caller sends it today | 200, 3,093,587 bytes of PDF |
| `/trans/downloadTestOrderPDF`, same query | **400 Bad Request** |
| `/trans/downloadTestOrderPDF`, same query plus `&clinic_id=` | **200, byte-identical: 3,093,587 bytes** |

So it is not a drop-in, and the whole difference is one parameter. The service token carries `customer_id: null` and `clinic_id: null`; the `/trans` route resolves identity through `resolveIdsForHttpOptional`, which falls back to the query when a claim is absent from the JWT, and the caller sends `customer_id` but not `clinic_id`. The proxy route reads `req.user` only and bypasses ownership via `isTrustedInternalCaller`, so it never needed the parameter.

Worth flagging for whoever picks this up: **the `clinic_id` value does not affect authorisation here.** The token is trusted-internal, `ownsSample` bypasses the ownership check, and the parameter exists only to satisfy the resolver. A required-but-inert parameter is a smell. The alternative fix — relaxing the `/trans` validation for trusted-internal callers — changes validation on a live route, so the smaller change is the caller supplying the parameter.

The change lands at `setting-consumer.controller.ts:15086`, where the query is built as a template literal.

A same-named `transService.downloadTestOrderPDF` exists and is a different thing — it calls the on-prem report server and is used by notifications and other report routes. It belongs to §6, not here.

---

## 6. The real end state for the report family

Three `/trans/*` report routes still address `192.168.60.77:8081/secure/nologin/…` — the legacy on-prem report server, unauthenticated by construction. That server, not the wrappers in front of it, is the thing worth retiring: every route pointing at it is a dependency on an unauthenticated on-prem box reachable only because something in front of it is doing the authorising.

So `/trans/*` is a **holding position, not the end state.** It is the right place for these operations today — the ownership gate is implemented there, and it is what the front end already calls — but the destination for the report family is `base-report-service`, which is already a real service with its own AKS deployment, its own authenticated external edge and its own report-generation pipeline. That is a conversation with the report team, sized on its own merits, and it is not a prerequisite for anything on this page.

What this page does *not* recommend is rebuilding the report family inside **trans v2**. Nineteen routes, a cross-tenant ownership gate, deep-link token resolution and PDF streaming, for zero latency benefit — the p95 on this family is spent in `lis-order` and `pdf-engine`, not in trans. Trans v2 holds report keys in its ConfigMap but reads none of them, so this would be a from-scratch re-implementation of a compliance gate, which is exactly where the spoofing bypass in §4.4 came from. Moving these operations toward their owning services is the better direction; moving them sideways into the other trans is not.

**End users cannot be pointed at the destination directly** for anything in this family, whichever service ends up owning it. The on-prem report server has no authentication, so sending customers there removes the cross-tenant gate rather than relocating it. Whoever owns the operation owns the gate with it.

---

## 7. Sequence

1. **Now.** Merge LIS-transformer PR #800 (logs `user-agent`, `x-forwarded-for` and the JWT subject on `/proxy/grpc/*`; log-only, tested). Open the equivalent for `/proxy/old-report/*` — the busiest endpoint in the family sits there and PR #800 does not cover it.
2. **2026-10-02.** VP-18320 removes the three dead `/proxy/grpc` routes after its announced two-week notice. The 10 dead `/proxy/old-report` routes can join it.
3. **~1 week after the logging lands.** Resolve the two open branches in §3 — the rule and both candidate destinations are already fixed; only the caller names are missing.
4. **Then.** One migration ticket per downstream owner, naming the target endpoint and a date, in the shape of VP-18320.
5. **In parallel, on other teams' calendars.** lis-order takes `downloadTestOrderPDF` (§5); the report team takes the `secure/nologin` dependencies (§6); billing moves to `crmapi` (§3).
6. **Last.** Delete the routes, then retire `cloud-local-proxy` once its caller list is complete and the 30-day zero-traffic clock has run.

---

## 8. Asks

- **Ingress access logs** — cloud and on-prem, for `api.vibrant-america.com/v1/lis/cloud-proxy` and `www.vibrant-america.com/lisapi/v1/lis/cloud-proxy`. This is the only thing that can enumerate `cloud-local-proxy`'s callers, and nothing downstream of it can start without that list.
- **lis-order team** — take `downloadTestOrderPDF` (§5). Two of your own documents are currently fetched separately and merged by trans.
- **Report team** — the three `/trans/*` routes still pointing at the unauthenticated on-prem report server (§6), and whether `base-report-service` is their successor.
- **Billing** — move `sendSkinPlacePatientOrders` off the proxy, carrying the payload rewrite in §4.3.
- **Anyone calling a `/proxy/*` route** — say so on VP-18320. Log retention here is 15 days, so a job that runs monthly is invisible to us; a reply is the only way we find out before it breaks.
- **Repo admins** — mark the `typecheck + unit tests` job as a required status check on `main` in both trans repos. Until then a red PR check is advisory, and a merge to `main` is a deploy.
