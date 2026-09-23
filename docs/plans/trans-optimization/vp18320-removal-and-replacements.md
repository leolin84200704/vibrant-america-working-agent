# VP-18320 — What gets deleted, and what replaces it

**Ticket:** VP-18320 · **Epic:** VP-18260 · **Repo:** `LIS-transformer` (trans v1)
**Announced:** 2026-09-18 · **Removal PR opens:** 2026-10-02 · **Ticket closes:** 2026-10-09
**Widened 2026-09-23** to include the ten unused `/proxy/old-report/*` routes, per the proposal
in comment 188522 which drew no objection in two days.

This page is the removal list. For every route it states what disappears, what a caller
should use instead, and — where the replacement is not byte-for-byte identical — exactly how
it differs. Nothing here is removed on the strength of a zero-traffic window alone; see §1.

---

## 1. Evidence, re-measured 2026-09-23

Counted from trans v1 **request logs**, not APM spans. Spans are sampled at roughly 0.4% and
understate sparse traffic by two orders of magnitude; every request writes a log line. Window:
the full 15 days Datadog retains, **2026-09-08 → 2026-09-23**. The `TRANS_PROXY_GRPC_MODE`
cutover that moved trans v2 onto direct gRPC landed 2026-09-16 22:03 UTC.

### `/proxy/grpc/*` — daily counts

| Route | 09-08 → 09-16 (pre-cutover) | 09-17 → 09-23 (post-cutover) | Verdict |
|---|---|---|---|
| `getTestStatus` | 129 – 1,876/day, **10,842 total** | **0 every day, 7 days running** | Remove |
| `getQuestionaireBySampleId` | the same series, never differing by more than 1, **10,845 total** | **0 every day, 7 days running** | Remove |
| `listTnpCode` | **0 every day** | **0 every day** | Remove |
| `getKitStatus` | ≈2× the first two (260 – 3,700/day) | 7 – 15/day | Keep |
| `getPatientTestsResult` | 1 – 5/day, flat | 1 – 5/day, flat | Keep |
| `sendSkinPlacePatientOrders` | 0 | 0 | Keep — see §4 |

**What makes the first two safe is the lockstep, not the zeros.** Two routes tracking each
other to within one call on all nine pre-cutover days, with a third running at exactly twice
their rate, is one caller's fixed per-sample pattern — trans v2's `patientProfile` — not a
population of callers. A second, independent consumer would break the lockstep on the days it
ran. It never breaks, and both went to zero the day after that caller moved. The zero streak
is now **7 consecutive days**, up from the 2 the announcement was written on.

`listTnpCode` is a different argument: zero for the whole window *including before the
cutover*, and no caller in any of the 63 repos searched on the dev machine. Note that
`LIS-backend-results-grpc` implements a `listTnpCode` — that is the downstream service, not a
caller.

### `/proxy/old-report/*` — 15-day totals

| Route | 15-day traffic | Verdict |
|---|---|---|
| `downloadTestOrderPDF` | **20,669** (≈1,380/day) | **Keep** — see §4 |
| the other ten | **0** | Remove |

### What this evidence does not cover

Datadog log retention stops at 15 days — a 35-day query returns nothing before the retention
edge, on flex storage too — so **a caller that runs monthly is invisible to this measurement**,
and the code search only covers repos cloned locally. That gap is the entire reason this is
announced two weeks ahead rather than simply deleted, and it is why §6 requires the counts to
be re-run on the day the PR opens rather than trusting this page.

---

## 2. Group A — three `/proxy/grpc` routes

No replacement is needed for any of the three: the only caller already moved, and it moved to
the destination rather than to another wrapper.

| Deleted | What it talked to | Replacement for anyone still on it |
|---|---|---|
| `GET /proxy/grpc/getTestStatus` | test-connect gRPC `getTestStatus` | Call the gRPC service directly. Trans v2's `proxy-grpc.service.ts` is the worked example — note the proto field name differs from the shipping service and `sampleId` goes as a **number** there |
| `GET /proxy/grpc/getQuestionaireBySampleId` | shipping gRPC `getQuestionaireBySampleId` | Same service, but `sample_id` goes as a **string**. Same file |
| `GET /proxy/grpc/listTnpCode` | test-connect gRPC `listTnpCode` | Call it directly. No caller exists to migrate |

**Two things must travel with any such migration, or the move is not equivalent:**

1. **JWT → gRPC metadata.** `createMetadataForCoresampleV2` in `src/proxy/proxy.service.ts`
   propagates the caller's JWT subject to core. It is *not* an ownership check — the
   `/proxy/grpc` family carries authentication only.
2. **A proto3 normalisation on kit lookups.** proto3 omits empty repeated fields, so a PO with
   no shipped packages arrives with `packages === undefined` and consumers crash on `.length`.
   The wrapper fills it with an empty array. Omitting this is Sentry #68038. (Applies to
   `getKitStatus`, which is staying — listed here so the recipe stays in one place.)

Trans v2 PR #629 carried both across line by line, and the shadow comparison that followed
agreed with the old path on 3,470 of 3,473 real requests. It worked because someone compared
it line by line, not because the layer is thin.

---

## 3. Group B — ten `/proxy/old-report` routes

Every one of the ten has a same-named twin under `/trans/*` in the same service, served by
`trans-reports.controller.ts`. **The replacement is the twin.**

The twins are not a parallel copy of the logic: eight of them call `TransService`, which
delegates into the very same `OldReportProxyService` methods the proxy handlers call, and two
call `OldReportProxyService` directly. The downstream, the generated document and the env keys
are therefore identical. What the `/trans` path adds on top is a navigator permission gate,
Kafka audit events and language resolution — so the copy being deleted is the *less* audited
of the two.

| Deleted route | Replacement | Reaches | Drop-in? |
|---|---|---|---|
| `GET /proxy/old-report/getRequisitionForm` | `GET /trans/getRequisitionForm` | `OldReportProxyService.getRequisitionForm` (direct, same call) | Yes |
| `GET /proxy/old-report/GenerateBatchReqOrReportV2` | `GET /trans/GenerateBatchReqOrReportV2` | `TransService.GenerateBatchReqOrReport` → `generateBatchReqOrReport` / `runGenerateBatchReqOrderSummary` | Yes |
| `GET /proxy/old-report/GenerateOnlineZipDownloadV2` | `GET /trans/GenerateOnlineZipDownloadV2` | `TransService.generateOnlineZip` → `generateOnlineZip` / `runGenerateOnlineZipOrderSummary` | Yes |
| `GET /proxy/old-report/getOrderSummaryReportZip` | `GET /trans/getOrderSummaryReportZip` | `TransService.generateOnlineZip` | **No — see (a)** |
| `GET /proxy/old-report/GetSpecificReports` | `GET /trans/GetSpecificReports` | `TransService.GetSpecificReports` → `GetSpecificReports` | **No — see (b)** |
| `GET /proxy/old-report/GenerateOnlineSummaryReport` | `GET /trans/GenerateOnlineSummaryReport` | `TransService.GenerateOnlineSummaryReport` → same | Yes |
| `GET /proxy/old-report/GenerateProducctSummaryReport` | `GET /trans/GenerateProducctSummaryReport` | `TransService.GenerateProducctSummaryReport` → same | Yes |
| `GET /proxy/old-report/GenerateProducctReport` | `GET /trans/GenerateProducctReport` | `TransService.GenerateProducctReport` → same | Yes |
| `GET /proxy/old-report/checkIfPersonalizedReportCanBeCreated` | `GET /trans/checkIfPersonalizedReportCanBeCreated` | `TransService.checkIfPersonalizedReportCanBeCreated` → same | Yes |
| `GET /proxy/old-report/oneClickPersonalizedReport` | `GET /trans/oneClickPersonalizedReport` | `OldReportProxyService.oneClickPersonalizedReport` (direct, same call) | Yes |

**(a) `getOrderSummaryReportZip` — different scoping mechanism.** The proxy copy calls
`generateOnlineZipNoJWT` and scopes the downstream fetch by `customer_id_arr`. In the `/trans`
twin that call is commented out and the JWT-scoped `generateOnlineZip` runs instead. Same
artefact, different way of deciding whose samples are in it. Both routes are at zero traffic,
so nothing is affected today — but a caller arriving from the proxy copy would be scoped by
their JWT rather than by the query parameter, which is the safer of the two and worth saying
out loud rather than discovering.

**(b) `GetSpecificReports` — different response shape.** The proxy copy streams the raw `.gz`
back to the caller. The `/trans` twin unzips it, parses it and returns **JSON**. A caller
moving across has to stop unzipping. This is the only route on the list where the replacement
changes what comes over the wire.

---

## 4. What explicitly stays

Deleting a handler must not take its service layer with it. Everything in this section is
still live after the PR.

- **`GET /proxy/old-report/downloadTestOrderPDF`** — ≈1,380 requests/day from
  `LIS-setting-consumer`, confirmed by attribution logging, not inferred. Its migration is a
  separate piece of work: `/trans/downloadTestOrderPDF` returns **400** on the caller's exact
  query string and **200 with a byte-identical 3,093,587-byte PDF** once `&clinic_id=` is
  added. That one-parameter change belongs to the setting-consumer ticket, not to this one.
- **`OldReportProxyService` in full, and every `process.env` key it reads** —
  `Get_Requisition`, `url_GenerateBatchReqOrReportV2`, `url_GenerateOnlineZipDownloadV2`,
  `url_downloadTestOrderPDF`, `url_GetSpecificReports`, `url_generateOnlineSummaryReport`,
  `url_get_product_report`, `url_order_summary_new`, `url_order_summary_new_redraw`,
  `checkIfPersonalizedReportCanBeCreated`, `oneClickPersonalizedReport`. The `/trans` twins
  reach these same methods. **Deleting any of them breaks live routes**, which is the one way
  this PR could cause an incident.
- **`assertSamplesOwned` and `isInternalCaller` on the controller** — `downloadTestOrderPDF`
  still calls them.
- **`ProxyCallerLogInterceptor`** — still bound to the controller class for the surviving route.
- **`/proxy/grpc/getKitStatus`, `/proxy/grpc/getPatientTestsResult`** — both still take traffic
  from `LIS-setting-consumer`; their migration is a code change in that repo, not a config swap.
- **`/proxy/grpc/sendSkinPlacePatientOrders`** — at zero, but it is the *consolidation target*
  that `LIS-backend-billing` is due to be repointed onto, not a removal candidate. Its known
  caller currently posts to the on-prem proxy instead, which is why the route reads zero. A
  zero here is not evidence of death.

---

## 5. The shape of the removal PR

**Delete**

- `src/proxy/proxy.controller.ts` — the three handlers `getTestStatus`,
  `getQuestionaireBySampleId`, `listTnpCode`, and any `ProxyService` methods left with no
  other caller after that.
- `src/proxy/old-report.controller.ts` — the ten handlers listed in §3. Leave the class, the
  two private helpers, the interceptor binding and the `downloadTestOrderPDF` handler.
- `src/proxy/dto/old-report.dto.ts` — `SampleIdQuery`, `GenerateZipQuery`,
  `GenerateZipv2Query`, `GetSpecificReportsQuery`, `GenerateSummaryReportQuery` become dead
  once the ten handlers are gone. **Keep `GenerateOrderpdfQuery`** (the surviving route) and
  **keep `GenerateProducctReportQuery`** (imported by `old-report.service.ts`, which stays).
  The `/trans` twins use their own DTO types, so nothing there is affected.

**Do not touch**

- `src/proxy/old-report.service.ts`, `src/trans/trans.service.ts`,
  `src/trans/trans-reports.controller.ts`, and every env key in §4.

**Tests**

Removing routes is not covered by asserting that the remaining ones still pass. The PR should
also assert the deleted paths now 404 and, for `downloadTestOrderPDF`, that the response is
still the same streamed object rather than a buffered copy — assert **object identity**
(`expect(returned).toBe(handlerObservable)`), because identity is the property that proves the
stream is not being wrapped, delayed or re-sent. Asserting the emitted value only proves this
one call happened to work.

---

## 6. Config keys

ConfigMap keys that point at the three `/proxy/grpc` routes go with them. From the cluster
inventory taken earlier in this epic, the keys to look for are `proxy_getteststatus`,
`proxy_getQuestionaire` and `proxy_getTnpCode`, in the trans v2 and setting-consumer
ConfigMaps on both prod and staging.

**Re-inventory before editing; do not delete from this list.** Four ConfigMaps were edited on
2026-09-22 for VP-18324, so the snapshot this list came from is already out of date. A key
that still resolves is a key something may still read.

`listTnpCode` has no ConfigMap key in the inventory at all, consistent with its having no
caller.

---

## 7. Sequence on the day

1. **Re-run the counts** over a fresh 15-day window — the three `/proxy/grpc` routes and the
   ten `/proxy/old-report` routes. Any non-zero row drops out of the PR; it does not get
   explained away.
2. Check VP-18320 for replies. A comment before 2026-10-02 means that route stays until its
   caller has moved.
3. Open the PR against `main` with the §5 scope. `main` is deploy-on-merge in this repo, so
   the PR is the deploy.
4. After deploy: confirm the deleted paths 404 in production, confirm
   `downloadTestOrderPDF` still returns PDFs at its usual rate, and confirm no new 4xx/5xx on
   the `/trans/*` twins.
5. Re-inventory and remove the dead ConfigMap keys (§6) as a separate change, after the code
   is live.

**Rollback** is a revert of the PR plus a deploy. No data is touched, no schema changes, no
config is removed in the same change as the code — which is the point of splitting step 5 out.

---

## 8. Refs

- Phase 1 Detail — Remove the Detours (item P1-C), Confluence LIS 2696740867
- Retiring /proxy and cloud-local-proxy — Classification and Migration Targets, Confluence LIS 2697166874
- Consumer inventory and migration runbook, Confluence LIS 2697461770
- `LIS-transformer` PR #800 / #801 — caller attribution on the routes that are staying
- VP-18320 comment 188522 — caller identification and the widening proposal
